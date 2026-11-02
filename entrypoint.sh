#!/bin/bash
set -e

WARP_PORT="${WARP_PORT:-40000}"
INTERNAL_PORT=$((WARP_PORT + 1))

PIDS=()

cleanup() {
    trap - EXIT
    if (( ${#PIDS[@]} )); then
        kill "${PIDS[@]}" 2>/dev/null || true
        wait "${PIDS[@]}" 2>/dev/null || true
    fi
}

trap cleanup EXIT
trap 'exit 143' TERM
trap 'exit 130' INT

echo "[*] Starting warp-svc..."
warp-svc --accept-tos &
WARP_PID=$!
PIDS+=("$WARP_PID")

check_warp() {
    if ! kill -0 "$WARP_PID" 2>/dev/null; then
        echo "[!] warp-svc exited during startup" >&2
        exit 1
    fi
}

echo "[*] Waiting for warp-svc to respond..."
DEADLINE=$((SECONDS + 30))
# A socket can survive a container restart; wait for a successful RPC.
until timeout 2s warp-cli --accept-tos status > /dev/null 2>&1; do
    check_warp
    if (( SECONDS >= DEADLINE )); then
        echo "[!] Timed out waiting for warp-svc to respond" >&2
        exit 1
    fi
    sleep 1
done

echo "[*] Registering device..."
DEADLINE=$((SECONDS + 60))
while [[ ! -f /var/lib/cloudflare-warp/reg.json ]]; do
    check_warp
    if timeout 10s warp-cli --accept-tos registration new; then
        break
    fi
    if (( SECONDS >= DEADLINE )); then
        echo "[!] Timed out registering device" >&2
        exit 1
    fi
    sleep 5
done

echo "[*] Configuring proxy mode on port ${INTERNAL_PORT}..."
warp-cli --accept-tos mode proxy
warp-cli --accept-tos proxy port "${INTERNAL_PORT}"

echo "[*] Connecting..."
warp-cli --accept-tos connect
warp-cli --accept-tos dns log disable

echo "[*] Forwarding ${WARP_PORT} -> ${INTERNAL_PORT} via rinetd..."
echo "0.0.0.0 ${WARP_PORT} 127.0.0.1 ${INTERNAL_PORT}" > /etc/rinetd.conf

rinetd -f -c /etc/rinetd.conf &
PIDS+=("$!")

STATUS=0
wait -n "${PIDS[@]}" || STATUS=$?
echo "[!] A proxy process exited (status ${STATUS}); stopping container" >&2
exit 1
