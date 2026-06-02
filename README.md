# docker-cloudflare-warp-proxy

Docker image to run cloudflare-warp in proxy mode.

## Usage

Run the container using the following command. It is highly recommended to mount a volume for registration persistence and add necessary network capabilities.

```bash
docker run -d \
  --name=cloudflare-warp \
  --restart=always \
  --cap-add=NET_ADMIN \
  --sysctl net.ipv6.conf.all.disable_ipv6=0 \
  -v warp_data:/var/lib/cloudflare-warp \
  -e WARP_PORT=40000 \
  -p 40000:40000 \
  andsky/cloudflare-warp-proxy:latest
```

## Environment Variables

- `WARP_PORT`: The local port exposed by the SOCKS5 proxy (default: `40000`)

## Test Connection

You can verify the connection is routed through Cloudflare WARP using `curl`:

```bash
curl --socks5 127.0.0.1:40000 https://www.cloudflare.com/cdn-cgi/trace
```
(Look for `warp=on` or `warp=plus` in the output)
