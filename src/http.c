#include "app.h"
#include <arpa/inet.h>
#include <errno.h>
#include <limits.h>
#include <netinet/in.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>

#define HEADER_LIMIT 8192
static volatile sig_atomic_t running = 1;
static void stop_server(int signum) { (void)signum; running = 0; }
void http_stop(void) { running = 0; }

static int send_all(int fd, const char *buffer, size_t length) {
    while (length) {
        ssize_t count = send(fd, buffer, length, MSG_NOSIGNAL);
        if (count < 0 && errno == EINTR) continue;
        if (count <= 0) return 0;
        buffer += count; length -= (size_t)count;
    }
    return 1;
}

static void send_response(int fd, int status, const char *type, const char *body, size_t length) {
    const char *reason = status < 300 ? "OK" : status == 404 ? "Not Found" : "Error";
    char header[1400];
    int count = snprintf(header, sizeof(header),
        "HTTP/1.1 %d %s\r\nContent-Type: %s\r\nContent-Length: %zu\r\nConnection: close\r\n"
        "Cache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\nReferrer-Policy: no-referrer\r\n"
        "Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'\r\n\r\n",
        status, reason, type, length);
    if (count > 0 && (size_t)count < sizeof(header) && send_all(fd, header, (size_t)count)) send_all(fd, body, length);
}

static void send_error(int fd, int status, const char *message) {
    Response result = error_response(status, message);
    const char *body = result.body ? result.body : "{\"error\":\"Memória insuficiente.\"}";
    send_response(fd, result.status, "application/json; charset=utf-8", body, strlen(body));
    free(result.body);
}

static int local_origin(const char *value, int port) {
    char a[64], b[64];
    snprintf(a, sizeof(a), "http://127.0.0.1:%d", port);
    snprintf(b, sizeof(b), "http://localhost:%d", port);
    return !strcmp(value, a) || !strcmp(value, b);
}

static void static_file(App *app, int fd, const Request *req) {
    const char *name = NULL, *type = NULL;
    if (!strcmp(req->path, "/") || !strcmp(req->path, "/index.html")) { name = "index.html"; type = "text/html; charset=utf-8"; }
    else if (!strcmp(req->path, "/app.js")) { name = "app.js"; type = "text/javascript; charset=utf-8"; }
    else if (!strcmp(req->path, "/style.css")) { name = "style.css"; type = "text/css; charset=utf-8"; }
    else if (!strcmp(req->path, "/favicon.svg")) { name = "favicon.svg"; type = "image/svg+xml"; }
    if (!name) { send_error(fd, 404, "Página não encontrada."); return; }
    if (strcmp(req->method, "GET")) { send_error(fd, 405, "Método não permitido."); return; }
    char path[PATH_MAX];
    int n = snprintf(path, sizeof(path), "%s/%s", app->web_root, name);
    if (n < 0 || (size_t)n >= sizeof(path)) { send_error(fd, 500, "Caminho da interface inválido."); return; }
    FILE *file = fopen(path, "rb");
    if (!file) { send_error(fd, 404, "Arquivo da interface não encontrado. Execute a partir da pasta do projeto."); return; }
    if (fseek(file, 0, SEEK_END) != 0) { fclose(file); send_error(fd, 500, "Falha ao ler arquivo."); return; }
    long size = ftell(file);
    if (size < 0 || size > 2097152 || fseek(file, 0, SEEK_SET) != 0) { fclose(file); send_error(fd, 500, "Arquivo inválido."); return; }
    char *content = malloc((size_t)size + 1);
    if (!content) { fclose(file); send_error(fd, 500, "Memória insuficiente."); return; }
    size_t read_size = fread(content, 1, (size_t)size, file);
    fclose(file);
    if (read_size == (size_t)size) send_response(fd, 200, type, content, read_size);
    else send_error(fd, 500, "Falha ao ler a interface.");
    free(content);
}

static void handle_client(App *app, int fd, int port) {
    char *buffer = calloc(HEADER_LIMIT + MAX_BODY + 1, 1);
    if (!buffer) { send_error(fd, 500, "Memória insuficiente."); return; }
    size_t used = 0;
    char *header_end = NULL;
    while (!header_end) {
        if (used >= HEADER_LIMIT) { send_error(fd, 431, "Cabeçalho muito grande."); goto done; }
        ssize_t count = recv(fd, buffer + used, HEADER_LIMIT - used, 0);
        if (count <= 0) { send_error(fd, 400, "Requisição incompleta."); goto done; }
        used += (size_t)count;
        buffer[used] = '\0';
        header_end = strstr(buffer, "\r\n\r\n");
    }
    size_t header_length = (size_t)(header_end + 4 - buffer);
    Request req = {0};
    char target[2560], version[16], extra;
    char *line_end = strstr(buffer, "\r\n");
    if (!line_end) { send_error(fd, 400, "Requisição inválida."); goto done; }
    *line_end = '\0';
    if (sscanf(buffer, "%7s %2559s %15s %c", req.method, target, version, &extra) != 3 ||
        (strcmp(version, "HTTP/1.1") && strcmp(version, "HTTP/1.0")) || target[0] != '/') {
        send_error(fd, 400, "Requisição HTTP inválida."); goto done;
    }
    char *question = strchr(target, '?');
    if (question) {
        *question++ = '\0';
        if (strlen(question) >= sizeof(req.query)) { send_error(fd, 414, "Endereço muito longo."); goto done; }
        strcpy(req.query, question);
    }
    if (strlen(target) >= sizeof(req.path)) { send_error(fd, 414, "Endereço muito longo."); goto done; }
    strcpy(req.path, target);
    size_t body_length = 0;
    int has_length = 0, content_json = 0, has_host = 0;
    for (char *line = line_end + 2; line < header_end; ) {
        char *end = strstr(line, "\r\n");
        if (!end) { send_error(fd, 400, "Cabeçalho inválido."); goto done; }
        *end = '\0';
        char *colon = strchr(line, ':');
        if (!colon) { send_error(fd, 400, "Cabeçalho inválido."); goto done; }
        *colon++ = '\0';
        while (*colon == ' ' || *colon == '\t') colon++;
        size_t value_len = strlen(colon);
        while (value_len && (colon[value_len-1] == ' ' || colon[value_len-1] == '\t')) colon[--value_len] = '\0';
        if (!strcasecmp(line, "Content-Length")) {
            char *number_end;
            errno = 0;
            unsigned long length = strtoul(colon, &number_end, 10);
            if (has_length || !*colon || *colon == '-' || *number_end || errno || length > MAX_BODY) {
                send_error(fd, length > MAX_BODY ? 413 : 400, "Tamanho do corpo inválido ou acima de 64 KiB."); goto done;
            }
            body_length = (size_t)length; has_length = 1;
        } else if (!strcasecmp(line, "Transfer-Encoding")) {
            send_error(fd, 400, "Transferência fragmentada não suportada."); goto done;
        } else if (!strcasecmp(line, "Content-Type")) {
            content_json = !strcasecmp(colon, "application/json") || !strncasecmp(colon, "application/json;", 17);
        } else if (!strcasecmp(line, "Origin") && !local_origin(colon, port)) {
            send_error(fd, 403, "Origem não autorizada."); goto done;
        } else if (!strcasecmp(line, "Host")) {
            char host[80];
            int host_length = snprintf(host, sizeof(host), "http://%s", colon);
            if (has_host || host_length < 0 || (size_t)host_length >= sizeof(host) || !local_origin(host, port)) {
                send_error(fd, 403, "Host não autorizado. Use localhost ou 127.0.0.1."); goto done;
            }
            has_host = 1;
        } else if (!strcasecmp(line, "Sec-Fetch-Site") && !strcasecmp(colon, "cross-site")) {
            send_error(fd, 403, "Acesso entre sites não permitido."); goto done;
        }
        line = end + 2;
    }
    if (!has_host) { send_error(fd, 400, "Cabeçalho Host obrigatório."); goto done; }
    while (used < header_length + body_length) {
        ssize_t count = recv(fd, buffer + used, header_length + body_length - used, 0);
        if (count <= 0) { send_error(fd, 400, "Corpo incompleto."); goto done; }
        used += (size_t)count;
    }
    buffer[header_length + body_length] = '\0';
    if (memchr(buffer + header_length, '\0', body_length)) { send_error(fd, 400, "Corpo inválido."); goto done; }
    req.body = buffer + header_length;
    if (!strncmp(req.path, "/api/", 5)) {
        if (body_length && !content_json) { send_error(fd, 415, "Utilize Content-Type application/json."); goto done; }
        Response response = api_route(app, &req);
        const char *body = response.body ? response.body : "{\"error\":\"Memória insuficiente.\"}";
        send_response(fd, response.status, "application/json; charset=utf-8", body, strlen(body));
        free(response.body);
    } else static_file(app, fd, &req);
done:
    free(buffer);
}

int http_run(App *app, const char *host, int port) {
    struct sigaction action = {0};
    action.sa_handler = stop_server;
    sigemptyset(&action.sa_mask);
    sigaction(SIGINT, &action, NULL); sigaction(SIGTERM, &action, NULL);
    signal(SIGPIPE, SIG_IGN);
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) { perror("socket"); return 1; }
    int reuse = 1;
    setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof(reuse));
    struct sockaddr_in address = {0};
    address.sin_family = AF_INET; address.sin_port = htons((unsigned short)port);
    if (inet_pton(AF_INET, host, &address.sin_addr) != 1) {
        fputs("Endereço de escuta inválido. Use um endereço IPv4, como 127.0.0.1 ou 0.0.0.0.\n", stderr);
        close(fd);
        return 1;
    }
    if (bind(fd, (struct sockaddr *)&address, sizeof(address)) < 0 || listen(fd, 32) < 0) {
        perror("Não foi possível iniciar o servidor"); close(fd); return 1;
    }
    printf("\n  VENDA • Controle de vendas %s\n  Abra http://127.0.0.1:%d\n  Ctrl+C para encerrar.\n\n", APP_VERSION, port);
    fflush(stdout);
    while (running) {
        fd_set set;
        FD_ZERO(&set); FD_SET(fd, &set);
        struct timeval wait = {1, 0};
        int ready = select(fd + 1, &set, NULL, NULL, &wait);
        if (ready < 0 && errno != EINTR) { perror("select"); close(fd); return 1; }
        if (ready <= 0) continue;
        int client = accept(fd, NULL, NULL);
        if (client < 0) continue;
        struct timeval timeout = {5, 0};
        setsockopt(client, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));
        setsockopt(client, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout));
        handle_client(app, client, port);
        close(client);
    }
    close(fd);
    puts("Servidor encerrado. Dados preservados no banco.");
    return 0;
}
