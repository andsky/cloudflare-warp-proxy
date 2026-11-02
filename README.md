# docker-cloudflare-warp-proxy

Docker image to run cloudflare-warp in proxy mode.

## Usage

Run with `NET_ADMIN` and the IPv6 setting shown below. Mounting
`/var/lib/cloudflare-warp` preserves registration when recreating the container.

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

## Restart Behavior

The entrypoint waits for the WARP daemon to respond before configuring the proxy.
If either `warp-svc` or `rinetd` exits, the container stops so its restart policy
can recover the service. Daemon output is available through `docker logs cloudflare-warp`.

## Tests

Run the startup and process lifecycle regression tests on Linux with Bash,
Python 3, and GNU coreutils installed:

```bash
python3 -m unittest discover -s tests -v
```
