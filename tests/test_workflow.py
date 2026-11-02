import os
from pathlib import Path
import re
import subprocess
import tempfile
import textwrap
import unittest


WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/docker-publish.yml"
MOCK_COMMANDS = r'''
dpkg-query() {
    printf '%s' "$TEST_PACKAGE_VERSION"
    return "$TEST_DPKG_EXIT"
}
warp-cli() {
    printf 'warp-cli 2026.8.2115.0\nBuild date: 2026-10-01\n'
    printf 'called' > "$TEST_CLI_MARKER"
}
'''


class WorkflowMetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        step = re.search(
            r"(?ms)^      - name: Prepare Docker image build metadata\n"
            r"(.*?)(?=^      - name:|\Z)",
            WORKFLOW.read_text(),
        ).group(1)
        cls.script = textwrap.dedent(step.split("        run: |\n", 1)[1])

    def run_metadata(self, version, dpkg_exit=0):
        with tempfile.TemporaryDirectory(prefix="warp metadata ") as directory:
            root = Path(directory)
            env_file = root / "github-env"
            cli_marker = root / "cli-called"
            env = os.environ.copy()
            env.update(
                GITHUB_ACTOR="test-owner",
                GITHUB_REPOSITORY="test-owner/cloudflare-warp-proxy",
                GITHUB_ENV=env_file.as_posix(),
                TEST_PACKAGE_VERSION=version,
                TEST_DPKG_EXIT=str(dpkg_exit),
                TEST_CLI_MARKER=cli_marker.as_posix(),
            )
            result = subprocess.run(
                [os.environ.get("TEST_BASH", "bash"), "-e", "-o", "pipefail", "-c",
                 MOCK_COMMANDS + self.script],
                env=env,
                text=True,
                capture_output=True,
                timeout=5,
            )
            return (
                result,
                env_file.read_text() if env_file.exists() else "",
                cli_marker.exists(),
            )

    def test_package_version_ignores_multiline_cli_output(self):
        result, content, cli_called = self.run_metadata("2026.8.2115.0")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(content.splitlines(), [
            "IMAGE_NAME=test-owner/cloudflare-warp-proxy",
            "IMAGE_NAME_VERSION=test-owner/cloudflare-warp-proxy:2026.8.2115.0",
        ])
        self.assertFalse(cli_called)

    def test_invalid_version_does_not_write_environment_file(self):
        for version in ("", "2026.8.2115.0\ndate:", "bad version", "1:2026.8", "x" * 129):
            with self.subTest(version=version):
                result, content, _ = self.run_metadata(version)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("::error::Invalid WARP package version", result.stdout)
                self.assertEqual(content, "")

    def test_package_query_failure_does_not_write_environment_file(self):
        result, content, _ = self.run_metadata("2026.8.2115.0", dpkg_exit=1)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(content, "")


if __name__ == "__main__":
    unittest.main()
