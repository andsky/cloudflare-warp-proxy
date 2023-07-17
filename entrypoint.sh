#!/bin/bash
warp-svc >> /dev/null &

while [[ ! -S /run/cloudflare-warp/warp_service ]]; do sleep 1; done


while [[ ! -f /var/lib/cloudflare-warp/reg.json ]]; do
    warp-cli --accept-tos register || sleep 5
done

warp-cli --accept-tos set-mode proxy
warp-cli --accept-tos set-proxy-port 40000

warp-cli --accept-tos connect
warp-cli --accept-tos disable-dns-log
warp-cli --accept-tos enable-always-on

while true; do
  if warp-cli --accept-tos status | grep 'Disconnected' > /dev/null; then
    warp-cli --accept-tos connect
  fi
  sleep 1
done
