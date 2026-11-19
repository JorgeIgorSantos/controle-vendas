#include "products.h"
#include "api_helpers.h"
#include <string.h>

Response get_products(App *app, const Request *req) {
    char search[121], state[16];
    if (query_param(req->query, "search", search, sizeof(search)) < 0 ||
        query_param(req->query, "status", state, sizeof(state)) < 0)
        return error_response(400, "Filtro de produtos inválido.");
    int active = -1;
    if (strcmp(state, "active") == 0) active = 1;
    else if (strcmp(state, "inactive") == 0) active = 0;
    else if (*state && strcmp(state, "all") != 0) return error_response(400, "Situação inválida.");
    sqlite3_stmt *stmt = db_prepare(app,
        "SELECT * FROM products WHERE (?1=-1 OR active=?1) AND "
        "(?2='' OR instr(lower(name),lower(?2))>0 OR instr(lower(sku),lower(?2))>0 "
        "OR instr(lower(category),lower(?2))>0) ORDER BY name COLLATE NOCASE,id");
    if (!stmt) return db_error();
    sqlite3_bind_int(stmt, 1, active);
    bind_text(stmt, 2, search);
    cJSON *rows = read_rows(stmt);
    return rows ? json_response(200, rows) : db_error();
}

Response get_product(App *app, int64_t id) {
    cJSON *rows = read_rows_by_id(app, "SELECT * FROM products WHERE id=?", id);
    if (!rows) return db_error();
    cJSON *product = take_first_row(rows);
    return product ? json_response(200, product) : error_response(404, "Produto não encontrado.");
}

static int parse_product(const cJSON *json, Product *product) {
    const cJSON *active = cJSON_GetObjectItemCaseSensitive(json, "active");
    if (!json_text(json, "sku", product->sku, sizeof(product->sku), 1) ||
        !json_text(json, "name", product->name, sizeof(product->name), 1) ||
        !json_text(json, "category", product->category, sizeof(product->category), 1) ||
        !json_integer(json, "price_cents", 1, MAX_PRICE_CENTS, &product->price_cents) ||
        !json_integer(json, "stock", 0, MAX_QUANTITY, &product->stock) ||
        (active && !cJSON_IsBool(active))) return 0;
    product->active = !active || cJSON_IsTrue(active);
    return 1;
}

Response save_product(App *app, const cJSON *json, int64_t id) {
    Product product = {.id = id};
    if (!parse_product(json, &product)) return error_response(400,
        "Informe código, nome, categoria, preço positivo em centavos e estoque inteiro entre 0 e 1.000.000.");
    const char *sql = product.id ?
        "UPDATE products SET sku=?1,name=?2,category=?3,price_cents=?4,stock=?5,active=?6,"
        "updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id=?7" :
        "INSERT INTO products(sku,name,category,price_cents,stock,active,min_stock) VALUES(?1,?2,?3,?4,?5,?6,0)";
    sqlite3_stmt *stmt = db_prepare(app, sql);
    if (!stmt) return db_error();
    bind_text(stmt, 1, product.sku);
    bind_text(stmt, 2, product.name);
    bind_text(stmt, 3, product.category);
    sqlite3_bind_int64(stmt, 4, product.price_cents);
    sqlite3_bind_int64(stmt, 5, product.stock);
    sqlite3_bind_int(stmt, 6, product.active);
    if (product.id) sqlite3_bind_int64(stmt, 7, product.id);
    int rc = sqlite3_step(stmt), changes = sqlite3_changes(app->db);
    sqlite3_finalize(stmt);
    if (rc == SQLITE_CONSTRAINT) return error_response(409, "Já existe um produto com este código. Use um código único.");
    if (rc != SQLITE_DONE) return db_error();
    if (product.id && !changes) return error_response(404, "Produto não encontrado.");
    Response response = get_product(app, product.id ? product.id : sqlite3_last_insert_rowid(app->db));
    if (!product.id && response.status == 200) response.status = 201;
    return response;
}

Response delete_product(App *app, int64_t id) {
    sqlite3_stmt *stmt = db_prepare(app, "DELETE FROM products WHERE id=?");
    if (!stmt) return db_error();
    sqlite3_bind_int64(stmt, 1, id);
    int rc = sqlite3_step(stmt), changes = sqlite3_changes(app->db);
    sqlite3_finalize(stmt);
    if (rc == SQLITE_CONSTRAINT) return error_response(409,
        "Este produto possui vendas no histórico. Edite e desative o produto para preservar os registros.");
    if (rc != SQLITE_DONE) return db_error();
    if (!changes) return error_response(404, "Produto não encontrado.");
    cJSON *result = cJSON_CreateObject();
    if (result) cJSON_AddBoolToObject(result, "deleted", 1);
    return json_response(200, result);
}
