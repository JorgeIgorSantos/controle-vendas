FROM gcc:14-bookworm AS build

WORKDIR /app
COPY Makefile ./
COPY include/ include/
COPY src/ src/
COPY vendor/ vendor/
RUN make -j2 backend

FROM node:24-bookworm-slim AS frontend

WORKDIR /app/web
COPY web/package*.json ./
RUN npm ci --include=dev
COPY web/ ./
RUN npm run build

FROM debian:bookworm-slim AS runtime

RUN mkdir -p /app/data && chown 10001:10001 /app/data

WORKDIR /app
COPY --from=build /app/build/vendas ./vendas
COPY --from=frontend /app/web/dist/browser/ web/dist/browser/
COPY --from=frontend /app/web/dist/3rdpartylicenses.txt web/dist/

USER 10001:10001
ENV PORT=8080
EXPOSE 8080
VOLUME ["/app/data"]

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD bash -ec 'exec 3<>/dev/tcp/127.0.0.1/$PORT; printf "GET /api/health HTTP/1.1\r\nHost: 127.0.0.1:%s\r\nConnection: close\r\n\r\n" "$PORT" >&3; IFS= read -r status <&3; [[ "$status" == "HTTP/1.1 200 "* ]]'

ENTRYPOINT ["/app/vendas"]
CMD ["--host", "0.0.0.0", "--db", "/app/data/vendas.db"]
