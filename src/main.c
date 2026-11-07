#include "app.h"
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv) {
    int port = 8080;
    const char *host = "127.0.0.1";
    const char *db_path = "data/vendas.db";
    App app = {.web_root = "web/dist/browser"};
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--help") == 0) {
            puts("Uso: ./build/vendas [--host 127.0.0.1] [--port 8080] [--db data/vendas.db] [--web web/dist/browser]\n"
                 "Abra http://127.0.0.1:8080 no navegador. Ctrl+C encerra o servidor.");
            return 0;
        } else if (i + 1 < argc && strcmp(argv[i], "--db") == 0) db_path = argv[++i];
        else if (i + 1 < argc && strcmp(argv[i], "--host") == 0) host = argv[++i];
        else if (i + 1 < argc && strcmp(argv[i], "--web") == 0) app.web_root = argv[++i];
        else if (i + 1 < argc && strcmp(argv[i], "--port") == 0) {
            char *end = NULL;
            errno = 0;
            long value = strtol(argv[++i], &end, 10);
            if (errno || *end || value < 1024 || value > 65535) {
                fputs("Porta inválida. Use um número entre 1024 e 65535.\n", stderr);
                return 1;
            }
            port = (int)value;
        } else {
            fprintf(stderr, "Opção inválida: %s. Consulte --help.\n", argv[i]);
            return 1;
        }
    }
    int result = 1;
    if (db_open(&app, db_path))
        result = http_run(&app, host, port);
    sqlite3_close(app.db);
    return result;
}
