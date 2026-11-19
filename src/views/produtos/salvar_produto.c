#include "views.h"

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
