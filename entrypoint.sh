#!/bin/bash
warp-svc &

while [[ ! -S /run/cloudflare-warp/warp_service ]]; do sleep 1; done


while [[ ! -f /var/lib/cloudflare-warp/reg.json ]]; do
    warp-cli --accept-tos register || sleep 5
done

warp-cli --accept-tos set-mode proxy
warp-cli --accept-tos set-proxy-port 40001

warp-cli --accept-tos connect
warp-cli --accept-tos disable-dns-log
warp-cli --accept-tos enable-always-on

socat TCP-LISTEN:40000,fork,reuseaddr TCP:127.0.0.1:40001
