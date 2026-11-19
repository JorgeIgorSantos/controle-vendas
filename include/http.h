#ifndef VENDA_HTTP_H
#define VENDA_HTTP_H

#include "models.h"

#define MAX_BODY 65536

typedef struct {
    char method[8];
    const char *path;
    const char *query;
    const char *body;
} Request;

typedef struct {
    int status;
    char *body;
} Response;

Response api_route(App *app, const Request *request);
Response json_response(int status, cJSON *json);
Response error_response(int status, const char *message);
Response db_error(void);
int http_run(App *app, const char *host, int port);
void http_stop(void);
int query_param(const char *query, const char *key, char *out, size_t capacity);
int valid_date(const char *s);
int date_filters(const Request *req, char *from, char *to);
int json_integer(const cJSON *object, const char *key, int64_t min, int64_t max, int64_t *out);
int json_text(const cJSON *object, const char *key, char *out, size_t capacity, int required);

#endif
