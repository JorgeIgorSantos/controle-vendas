#include "app.h"
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv) {
    const char *port_text = getenv("PORT");
    if (!port_text || !*port_text) port_text = "8080";
    const char *host = "127.0.0.1";
    const char *db_path = "data/vendas.db";
    const char *public_host = getenv("VENDA_PUBLIC_HOST");
    if (!public_host || !*public_host) public_host = getenv("RENDER_EXTERNAL_HOSTNAME");
    if (public_host && !*public_host) public_host = NULL;
    App app = {.web_root = "web/dist/browser", .public_host = public_host};
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--help") == 0) {
            puts("Uso: ./build/vendas [--host 127.0.0.1] [--port 8080] [--db data/vendas.db] [--web web/dist/browser]\n"
                 "Abra http://127.0.0.1:8080 no navegador. Ctrl+C encerra o servidor.");
            return 0;
        } else if (i + 1 < argc && strcmp(argv[i], "--db") == 0) db_path = argv[++i];
        else if (i + 1 < argc && strcmp(argv[i], "--host") == 0) host = argv[++i];
        else if (i + 1 < argc && strcmp(argv[i], "--web") == 0) app.web_root = argv[++i];
        else if (i + 1 < argc && strcmp(argv[i], "--port") == 0) {
            port_text = argv[++i];
        } else {
            fprintf(stderr, "Opção inválida: %s. Consulte --help.\n", argv[i]);
            return 1;
        }
    }
    char *end = NULL;
    errno = 0;
    long value = strtol(port_text, &end, 10);
    if (errno || *end || value < 1024 || value > 65535) {
        fputs("Porta inválida. Use um número entre 1024 e 65535.\n", stderr);
        return 1;
    }
    if (public_host && (strlen(public_host) > 253 ||
        strspn(public_host, "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-.") != strlen(public_host))) {
        fputs("O domínio público deve ser informado sem protocolo, porta ou caminho.\n", stderr);
        return 1;
    }
    int port = (int)value;
    int result = 1;
    if (db_open(&app, db_path))
        result = http_run(&app, host, port);
    sqlite3_close(app.db);
    return result;
}
