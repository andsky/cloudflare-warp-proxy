#!/bin/bash
set -e

WARP_PORT="${WARP_PORT:-40000}"
INTERNAL_PORT=$((WARP_PORT + 1))

echo "[*] Starting warp-svc..."
warp-svc --accept-tos >> /dev/null &

echo "[*] Waiting for warp-svc socket..."
TIMEOUT=30
ELAPSED=0
while [[ ! -S /run/cloudflare-warp/warp_service ]]; do
    sleep 1
    ELAPSED=$((ELAPSED + 1))
    if [[ $ELAPSED -ge $TIMEOUT ]]; then
        echo "[!] Timed out waiting for warp-svc socket" >&2
        exit 1
    fi
done

echo "[*] Registering device..."
while [[ ! -f /var/lib/cloudflare-warp/reg.json ]]; do
    warp-cli --accept-tos registration new && break || sleep 5
done

echo "[*] Configuring proxy mode on port ${INTERNAL_PORT}..."
warp-cli --accept-tos mode proxy
warp-cli --accept-tos proxy port "${INTERNAL_PORT}"

echo "[*] Connecting..."
warp-cli --accept-tos connect
warp-cli --accept-tos dns log disable

echo "[*] Forwarding ${WARP_PORT} -> ${INTERNAL_PORT} via rinetd..."
echo "0.0.0.0 ${WARP_PORT} 127.0.0.1 ${INTERNAL_PORT}" > /etc/rinetd.conf

exec rinetd -f -c /etc/rinetd.conf
