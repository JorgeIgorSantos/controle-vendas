#ifndef VENDA_APP_H
#define VENDA_APP_H

#include <stdint.h>
#include <stddef.h>
#include "sqlite3.h"
#include "cJSON.h"

#define APP_VERSION "1.0.0"
#define MAX_BODY 65536
#define MAX_ITEMS 200
#define MAX_QUANTITY 1000000
#define MAX_PRICE_CENTS 100000000
#define MAX_SALE_CENTS 9000000000000LL

/* Os valores monetários são inteiros em centavos, inclusive no banco. */
typedef struct {
    int64_t id;
    char sku[41];
    char name[121];
    char category[61];
    int64_t price_cents;
    int stock;
    int min_stock;
    int active;
    char notes[501];
} Product;

typedef struct {
    int64_t product_id;
    char sku[41];
    char name[121];
    int quantity;
    int64_t unit_price_cents;
    int64_t total_cents;
} SaleItem;

typedef struct {
    int64_t id;
    char customer[121];
    char payment_method[20];
    int64_t subtotal_cents;
    int64_t discount_cents;
    int64_t total_cents;
    char notes[501];
    SaleItem *items;
    size_t item_count;
} Sale;

typedef struct {
    sqlite3 *db;
    const char *web_root;
} App;

typedef struct {
    char method[8];
    char path[512];
    char query[2048];
    char *body;
} Request;

typedef struct {
    int status;
    char *body;
} Response;

int db_open(App *app, const char *path);
int db_seed(App *app);
int db_exec(App *app, const char *sql);
int db_prepare(App *app, sqlite3_stmt **stmt, const char *sql);
void db_close(App *app);
Response api_route(App *app, const Request *request);
Response json_response(int status, cJSON *json);
Response error_response(int status, const char *message);
int http_run(App *app, const char *host, int port);
void http_stop(void);
int query_param(const char *query, const char *key, char *out, size_t capacity);
int valid_date(const char *s);
int json_integer(const cJSON *object, const char *key, int64_t min, int64_t max, int64_t *out);
int json_text(const cJSON *object, const char *key, char *out, size_t capacity, int required);

#endif
