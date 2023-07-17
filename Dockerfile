FROM debian:bookworm-slim


RUN apt update && apt install -y curl gnupg2 lsb-release libcap2-bin
RUN curl -fsSL https://pkg.cloudflareclient.com/pubkey.gpg | gpg --yes --dearmor --output /usr/share/keyrings/cloudflare-warp-archive-keyring.gpg \
	&& echo "deb [arch=amd64 signed-by=/usr/share/keyrings/cloudflare-warp-archive-keyring.gpg] https://pkg.cloudflareclient.com/ $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/cloudflare-client.list \
	&& apt update \
	&& apt install -y cloudflare-warp \
	&& apt autoremove -y  \
	&& apt clean -y \
	&& rm -rf /var/lib/apt/lists/*

COPY --chmod=755 entrypoint.sh entrypoint.sh
EXPOSE 40000/tcp
CMD ["./entrypoint.sh"]
