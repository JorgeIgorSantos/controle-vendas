#ifndef VENDA_MODELS_H
#define VENDA_MODELS_H

#include <stdint.h>
#include <stddef.h>
#include "sqlite3.h"
#include "cJSON.h"

#define MAX_ITEMS 200
#define MAX_QUANTITY 1000000
#define MAX_PRICE_CENTS 100000000
#define MAX_SALE_CENTS 9000000000000LL

/* Os campos com sufixo _cents armazenam centavos inteiros, inclusive no banco. */
typedef struct {
    int64_t id;
    char sku[41];
    char name[121];
    char category[61];
    int64_t price_cents;
    int64_t stock;
    int active;
} Product;

typedef struct {
    int64_t product_id;
    int64_t quantity;
} SaleItem;

typedef struct {
    int64_t id;
    char customer[121];
    char payment_method[20];
    int64_t total_cents;
    SaleItem *items;
} Sale;

typedef struct {
    sqlite3 *db;
    const char *web_root;
    const char *public_host;
} App;

int db_open(App *app, const char *path);
int db_exec(App *app, const char *sql);
sqlite3_stmt *db_prepare(App *app, const char *sql);
/* Consome e finaliza o statement; quem recebe as linhas deve liberá-las. */
cJSON *read_rows(sqlite3_stmt *stmt);
void bind_text(sqlite3_stmt *stmt, int index, const char *value);
cJSON *read_rows_by_id(App *app, const char *sql, int64_t id);
/* Consome o array e transfere a primeira linha para quem chamou. */
cJSON *take_first_row(cJSON *rows);
cJSON *read_range(App *app, const char *sql, const char *from, const char *to, const char *search);

#endif
