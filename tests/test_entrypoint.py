import os
from pathlib import Path
import signal
import socket
import subprocess
import tempfile
import time
import unittest


ENTRYPOINT = Path(__file__).resolve().parents[1] / "entrypoint.sh"
MOCK_SERVICE = r'''#!/usr/bin/env python3
import os
from pathlib import Path
import signal
import sys
import time

state = Path(os.environ["TEST_STATE"])
service = Path(sys.argv[0]).name

def record(message):
    with (state / "events").open("a") as log:
        log.write(message + "\n")

def stop(signum, frame):
    record(service + " stopped")
    sys.exit(0)

def serve():
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    (state / (service + ".pid")).write_text(str(os.getpid()))

if service == "warp-svc":
    serve()
    if os.environ.get("DAEMON_FAIL"):
        sys.exit(23)
    time.sleep(float(os.environ.get("READY_DELAY", "0")))
    (state / "ready").write_text(str(os.getpid()))
    record("daemon ready")
    while True:
        signal.pause()

if service == "rinetd":
    serve()
    if os.environ.get("FORWARDER_FAIL"):
        sys.exit(17)
    record("forwarder ready")
    while True:
        signal.pause()

try:
    pid = int((state / "warp-svc.pid").read_text())
    os.kill(pid, 0)
    ready = (state / "ready").read_text() == str(pid)
except (OSError, ValueError):
    ready = False
if not ready:
    sys.exit(1)

args = sys.argv[1:]
record(" ".join(args))
if args[-2:] == ["registration", "new"]:
    if os.environ.get("REGISTRATION_FAIL"):
        sys.exit(1)
    (state / "reg.json").write_text("{}")
'''


@unittest.skipUnless(os.name == "posix", "requires Linux processes and Unix sockets")
class EntrypointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="warp-entrypoint-")
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        for name in ("warp-svc", "warp-cli", "rinetd"):
            executable = self.bin / name
            executable.write_text(MOCK_SERVICE)
            executable.chmod(0o755)

        source = ENTRYPOINT.read_text()
        for original, replacement in (
            ("/run/cloudflare-warp/warp_service", str(self.root / "warp_service")),
            ("/var/lib/cloudflare-warp/reg.json", str(self.root / "reg.json")),
            ("/etc/rinetd.conf", str(self.root / "rinetd.conf")),
        ):
            source = source.replace(original, replacement)
        self.script = self.root / "entrypoint.sh"
        self.script.write_text(source)
        self.log = (self.root / "output").open("w+")
        self.processes = []

    def tearDown(self):
        for process in self.processes:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=5)
        self.log.close()
        self.temp.cleanup()

    def launch(self, **options):
        env = os.environ.copy()
        env.update(TEST_STATE=str(self.root), PATH=f"{self.bin}:{env['PATH']}")
        env.update(options)
        process = subprocess.Popen(
            ["bash", str(self.script)],
            env=env,
            stdout=self.log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        self.processes.append(process)
        return process

    def events(self):
        path = self.root / "events"
        return path.read_text() if path.exists() else ""

    def wait_for(self, condition, timeout=8):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if condition():
                return
            time.sleep(0.05)
        self.log.seek(0)
        self.fail("condition timed out\n" + self.log.read())

    def wait_running(self):
        self.wait_for(lambda: "forwarder ready" in self.events())

    def daemon_pid(self):
        return int((self.root / "warp-svc.pid").read_text())

    def test_stale_socket_does_not_bypass_readiness(self):
        with socket.socket(socket.AF_UNIX) as stale:
            stale.bind(str(self.root / "warp_service"))
        (self.root / "reg.json").write_text("{}")

        process = self.launch(READY_DELAY="1")
        self.wait_running()

        self.assertIsNone(process.poll())
        events = self.events()
        self.assertLess(events.index("daemon ready"), events.index("mode proxy"))

    def test_daemon_exit_before_readiness_stops_container(self):
        process = self.launch(DAEMON_FAIL="1")
        self.assertNotEqual(process.wait(timeout=8), 0)
        self.assertFalse((self.root / "rinetd.pid").exists())

    def test_daemon_exit_stops_forwarder(self):
        process = self.launch()
        self.wait_running()
        os.kill(self.daemon_pid(), signal.SIGKILL)

        self.assertNotEqual(process.wait(timeout=8), 0)
        self.assertIn("rinetd stopped", self.events())

    def test_forwarder_exit_stops_daemon(self):
        process = self.launch(FORWARDER_FAIL="1")

        self.assertNotEqual(process.wait(timeout=8), 0)
        self.assertIn("warp-svc stopped", self.events())

    def test_sigterm_stops_both_processes(self):
        process = self.launch()
        self.wait_running()
        process.terminate()

        self.assertEqual(process.wait(timeout=8), 143)
        self.assertIn("warp-svc stopped", self.events())
        self.assertIn("rinetd stopped", self.events())

    def test_restart_preserves_registration(self):
        process = self.launch()
        self.wait_running()
        process.terminate()
        self.assertEqual(process.wait(timeout=8), 143)
        (self.root / "events").write_text("")

        restarted = self.launch(READY_DELAY="1")
        self.wait_running()

        self.assertIsNone(restarted.poll())
        self.assertNotIn("registration new", self.events())

    def test_daemon_exit_during_registration_stops_container(self):
        process = self.launch(REGISTRATION_FAIL="1")
        self.wait_for(lambda: "registration new" in self.events())
        os.kill(self.daemon_pid(), signal.SIGKILL)

        self.assertNotEqual(process.wait(timeout=8), 0)
        self.assertFalse((self.root / "rinetd.pid").exists())


if __name__ == "__main__":
    unittest.main()
