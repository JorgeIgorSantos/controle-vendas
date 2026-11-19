#include "views.h"
#include <stdlib.h>
#include <string.h>

static int payment_valid(const char *value) {
    return !strcmp(value, "pix") || !strcmp(value, "dinheiro") || !strcmp(value, "credito") || !strcmp(value, "debito");
}

static int deduct_stock(App *app, int64_t sale_id) {
    sqlite3_stmt *stmt = db_prepare(app,
        "UPDATE products SET stock=stock-(SELECT quantity FROM sale_items WHERE sale_id=?1 AND product_id=products.id),"
        "updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id IN (SELECT product_id FROM sale_items WHERE sale_id=?1)");
    if (!stmt) return 0;
    sqlite3_bind_int64(stmt, 1, sale_id);
    int rc = sqlite3_step(stmt);
    sqlite3_finalize(stmt);
    return rc == SQLITE_DONE;
}

Response create_sale(App *app, const cJSON *json) {
    Sale sale = {0};
    cJSON *items = cJSON_GetObjectItemCaseSensitive(json, "items");
    int count = cJSON_GetArraySize(items);
    if (!json_text(json, "customer", sale.customer, sizeof(sale.customer), 0) ||
        !json_text(json, "payment_method", sale.payment_method, sizeof(sale.payment_method), 1) ||
        !payment_valid(sale.payment_method) ||
        !cJSON_IsArray(items) || count < 1 || count > MAX_ITEMS)
        return error_response(400, "Informe de 1 a 200 produtos e uma forma de pagamento válida.");

    const cJSON *discount = cJSON_GetObjectItemCaseSensitive(json, "discount_cents");
    if (discount && (!cJSON_IsNumber(discount) || discount->valuedouble != 0))
        return error_response(400, "Novas vendas são registradas sem desconto.");

    sale.items = calloc((size_t)count, sizeof(*sale.items));
    if (!sale.items) return error_response(500, "Memória insuficiente para registrar a venda.");
    for (int i = 0; i < count; i++) {
        cJSON *item = cJSON_GetArrayItem(items, i);
        if (!cJSON_IsObject(item) || !json_integer(item, "product_id", 1, INT32_MAX, &sale.items[i].product_id) ||
            !json_integer(item, "quantity", 1, MAX_QUANTITY, &sale.items[i].quantity)) {
            free(sale.items); return error_response(400, "Produto ou quantidade inválida. Use quantidades inteiras positivas.");
        }
        for (int j = 0; j < i; j++) if (sale.items[j].product_id == sale.items[i].product_id) {
            free(sale.items); return error_response(400, "Produto repetido na venda. Agrupe as quantidades no mesmo item.");
        }
    }
    if (!db_exec(app, "BEGIN IMMEDIATE")) { free(sale.items); return db_error(); }
    const char *failure = NULL;
    int status = 500;
    sqlite3_stmt *stmt = db_prepare(app, "SELECT price_cents,stock,active FROM products WHERE id=?");
    if (!stmt) goto failed;
    for (int i = 0; i < count; i++) {
        SaleItem *item = &sale.items[i];
        sqlite3_bind_int64(stmt, 1, item->product_id);
        int rc = sqlite3_step(stmt);
        if (rc == SQLITE_DONE) { failure = "Um dos produtos não existe."; status = 404; goto failed; }
        if (rc != SQLITE_ROW) goto failed;
        if (!sqlite3_column_int(stmt, 2)) { failure = "Produto inativo não pode ser vendido."; status = 409; goto failed; }
        if (sqlite3_column_int(stmt, 1) < item->quantity) {
            failure = "Estoque insuficiente. Revise a quantidade dos itens."; status = 409; goto failed;
        }
        sale.total_cents += sqlite3_column_int64(stmt, 0) * item->quantity;
        if (sqlite3_reset(stmt) != SQLITE_OK) goto failed;
        if (sale.total_cents > MAX_SALE_CENTS) { failure = "O valor da venda ultrapassa o limite permitido."; status = 400; goto failed; }
    }
    sqlite3_finalize(stmt);
    stmt = NULL;
    stmt = db_prepare(app,
        "INSERT INTO sales(customer,payment_method,subtotal_cents,discount_cents,total_cents) VALUES(?1,?2,?3,0,?3)");
    if (!stmt) goto failed;
    bind_text(stmt, 1, sale.customer);
    bind_text(stmt, 2, sale.payment_method);
    sqlite3_bind_int64(stmt, 3, sale.total_cents);
    if (sqlite3_step(stmt) != SQLITE_DONE) goto failed;
    sqlite3_finalize(stmt); stmt = NULL;
    sale.id = sqlite3_last_insert_rowid(app->db);
    stmt = db_prepare(app,
        "INSERT INTO sale_items(sale_id,product_id,sku,name,quantity,unit_price_cents,total_cents) "
        "SELECT ?1,id,sku,name,?3,price_cents,?3*price_cents FROM products WHERE id=?2");
    if (!stmt) goto failed;
    sqlite3_bind_int64(stmt, 1, sale.id);
    for (int i = 0; i < count; i++) {
        SaleItem *item = &sale.items[i];
        sqlite3_bind_int64(stmt, 2, item->product_id);
        sqlite3_bind_int64(stmt, 3, item->quantity);
        if (sqlite3_step(stmt) != SQLITE_DONE || sqlite3_changes(app->db) != 1 ||
            sqlite3_reset(stmt) != SQLITE_OK) goto failed;
    }
    sqlite3_finalize(stmt); stmt = NULL;
    if (!deduct_stock(app, sale.id) || sqlite3_changes(app->db) != count ||
        !db_exec(app, "COMMIT")) goto failed;
    free(sale.items);
    Response response = get_sale(app, sale.id);
    if (response.status == 200) response.status = 201;
    return response;
failed:
    sqlite3_finalize(stmt);
    db_exec(app, "ROLLBACK");
    free(sale.items);
    return failure ? error_response(status, failure) : db_error();
}
