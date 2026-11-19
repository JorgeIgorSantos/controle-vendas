#include "app.h"
#include "products.h"
#include "sales.h"
#include "reports.h"
#include <errno.h>
#include <stdlib.h>
#include <string.h>

static int64_t resource_id(const char *path, const char *prefix) {
    size_t n = strlen(prefix);
    if (strncmp(path, prefix, n) != 0 || path[n] < '1' || path[n] > '9') return 0;
    errno = 0;
    char *end;
    long long id = strtoll(path + n, &end, 10);
    if (errno || *end || id <= 0 || id > INT32_MAX) return 0;
    return (int64_t)id;
}

Response api_route(App *app, const Request *req) {
    int get = strcmp(req->method, "GET") == 0;
    int post = strcmp(req->method, "POST") == 0;
    int put = strcmp(req->method, "PUT") == 0;
    int del = strcmp(req->method, "DELETE") == 0;
    int products = !strcmp(req->path, "/api/products");
    int sales = !strcmp(req->path, "/api/sales");
    int reports = !strcmp(req->path, "/api/reports");
    int health = !strcmp(req->path, "/api/health");
    if (post && !strcmp(req->path, "/api/shutdown")) {
        cJSON *json = cJSON_CreateObject();
        if (json) cJSON_AddStringToObject(json, "message", "Servidor encerrado. Dados preservados.");
        Response response = json_response(200, json);
        if (response.body) http_stop();
        return response;
    }
    if (get && health) {
        cJSON *json = cJSON_CreateObject();
        if (json) { cJSON_AddStringToObject(json, "status", "ok"); cJSON_AddStringToObject(json, "version", APP_VERSION); }
        return json_response(200, json);
    }
    if (get && reports) return get_report(app, req);
    if (get && products) return get_products(app, req);
    if (get && sales) return get_sales(app, req);
    int64_t product_id = resource_id(req->path, "/api/products/");
    int64_t sale_id = resource_id(req->path, "/api/sales/");
    if (product_id && get) return get_product(app, product_id);
    if (product_id && del) return delete_product(app, product_id);
    if (sale_id && get) return get_sale(app, sale_id);
    if ((post && (products || sales)) || (put && product_id)) {
        cJSON *json = cJSON_ParseWithOpts(req->body, NULL, 1);
        if (!cJSON_IsObject(json)) { cJSON_Delete(json); return error_response(400, "Envie um objeto JSON válido."); }
        Response response = sales ? create_sale(app, json) : save_product(app, json, product_id);
        cJSON_Delete(json);
        return response;
    }
    if (product_id || sale_id || products || sales || reports || health)
        return error_response(405, "Operação não permitida para este recurso.");
    return error_response(404, "Recurso não encontrado.");
}
