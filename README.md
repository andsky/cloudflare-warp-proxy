# docker-cloudflare-warp-proxy

Docker image to run cloudflare-warp in proxy mode

## Usage

```
docker run -d --restart=always --name=cloudflare-warp -p 40000:40000 andsky/cloudflare-warp-proxy:latest
```



curl --socks5 127.0.0.1:40000 https://www.cloudflare.com/cdn-cgi/trace
