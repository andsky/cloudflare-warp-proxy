FROM debian:bookworm
#FROM debian:bookworm AS build

RUN apt update && apt install -y curl gnupg2 lsb-release libcap2-bin
RUN curl -fsSL https://pkg.cloudflareclient.com/pubkey.gpg | gpg --yes --dearmor --output /usr/share/keyrings/cloudflare-warp-archive-keyring.gpg \
	&& echo "deb [arch=amd64 signed-by=/usr/share/keyrings/cloudflare-warp-archive-keyring.gpg] https://pkg.cloudflareclient.com/ $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/cloudflare-client.list \
	&& apt update \
	&& apt install -y cloudflare-warp


#FROM debian:bookworm-slim
#RUN apt update && apt install -y --no-install-recommends socat libdbus-1-3 libnss3-tools libnspr4 
RUN apt install -y  socat
RUN apt autoremove -y && \
	apt clean -y &&\
	rm -rf /var/lib/{apt,dpkg,cache,log}

#COPY --from=build /usr/bin/warp-cli /usr/bin/warp-svc /usr/local/bin/
COPY --chmod=755 entrypoint.sh entrypoint.sh
EXPOSE 40000/tcp
ENTRYPOINT ["/entrypoint.sh"]
