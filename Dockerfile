FROM debian:trixie-slim

LABEL maintainer="andsky"
LABEL description="Cloudflare WARP SOCKS5 proxy in Docker"

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl gnupg2 lsb-release ca-certificates rinetd && \
    curl -fsSL https://pkg.cloudflareclient.com/pubkey.gpg \
        | gpg --yes --dearmor --output /usr/share/keyrings/cloudflare-warp-archive-keyring.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/cloudflare-warp-archive-keyring.gpg] https://pkg.cloudflareclient.com/ $(lsb_release -cs) main" \
        | tee /etc/apt/sources.list.d/cloudflare-client.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends cloudflare-warp && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY --chmod=755 entrypoint.sh /entrypoint.sh

ENV WARP_PORT=40000

EXPOSE ${WARP_PORT}/tcp

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS --socks5 127.0.0.1:$((WARP_PORT + 1)) https://www.cloudflare.com/cdn-cgi/trace | grep -qE "warp=(on|plus)" || exit 1

ENTRYPOINT ["/entrypoint.sh"]
