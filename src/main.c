#include "app.h"
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv) {
    int port = 8080, demo = 0;
    const char *host = "127.0.0.1";
    const char *db_path = "data/vendas.db";
    App app = {NULL, "web"};
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--demo") == 0) demo = 1;
        else if (strcmp(argv[i], "--help") == 0) {
            puts("Uso: ./build/vendas [--host 127.0.0.1] [--port 8080] [--db data/vendas.db] [--web web] [--demo]\n"
                 "Abra http://127.0.0.1:8080 no navegador. Ctrl+C encerra o servidor.\n"
                 "--demo cria exemplos somente se o banco estiver vazio.");
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
    if (!db_open(&app, db_path) || (demo && !db_seed(&app))) { db_close(&app); return 1; }
    int result = http_run(&app, host, port);
    db_close(&app);
    return result;
}
