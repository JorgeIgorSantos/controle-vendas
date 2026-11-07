#include "app.h"
#include <errno.h>
#include <stdlib.h>
#include <string.h>

static Response db_error(void) { return error_response(500, "Não foi possível concluir a operação no banco de dados."); }

/* Consome e finaliza o statement depois de converter o resultado. */
static cJSON *read_rows(sqlite3_stmt *stmt) {
    cJSON *rows = cJSON_CreateArray();
    int rc = SQLITE_NOMEM;
    while (rows && (rc = sqlite3_step(stmt)) == SQLITE_ROW) {
        cJSON *row = cJSON_CreateObject();
        if (!row) break;
        for (int i = 0; i < sqlite3_column_count(stmt); i++) {
            const char *name = sqlite3_column_name(stmt, i);
            switch (sqlite3_column_type(stmt, i)) {
                case SQLITE_INTEGER:
                    if (!strcmp(name, "active")) cJSON_AddBoolToObject(row, name, sqlite3_column_int(stmt, i));
                    else cJSON_AddNumberToObject(row, name, (double)sqlite3_column_int64(stmt, i));
                    break;
                case SQLITE_FLOAT: cJSON_AddNumberToObject(row, name, sqlite3_column_double(stmt, i)); break;
                case SQLITE_NULL: cJSON_AddNullToObject(row, name); break;
                default: cJSON_AddStringToObject(row, name, (const char *)sqlite3_column_text(stmt, i));
            }
        }
        if (!cJSON_AddItemToArray(rows, row)) {
            cJSON_Delete(row);
            break;
        }
    }
    sqlite3_finalize(stmt);
    if (rc == SQLITE_DONE) return rows;
    cJSON_Delete(rows);
    return NULL;
}

static void bind_text(sqlite3_stmt *stmt, int index, const char *value) {
    sqlite3_bind_text(stmt, index, value, -1, SQLITE_TRANSIENT);
}

static cJSON *read_rows_by_id(App *app, const char *sql, int64_t id) {
    sqlite3_stmt *stmt = db_prepare(app, sql);
    if (!stmt) return NULL;
    sqlite3_bind_int64(stmt, 1, id);
    return read_rows(stmt);
}

static cJSON *take_first_row(cJSON *rows) {
    cJSON *row = cJSON_DetachItemFromArray(rows, 0);
    cJSON_Delete(rows);
    return row;
}

static Response get_products(App *app, const Request *req) {
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

static Response get_product(App *app, int64_t id) {
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

static Response save_product(App *app, const cJSON *json, int64_t id) {
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

static Response delete_product(App *app, int64_t id) {
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

static int date_filters(const Request *req, char *from, char *to) {
    int a = query_param(req->query, "from", from, 11);
    int b = query_param(req->query, "to", to, 11);
    if (a < 0 || b < 0 || (a && !valid_date(from)) || (b && !valid_date(to))) return 0;
    if (!a) strcpy(from, "1900-01-01");
    if (!b) strcpy(to, "9999-12-31");
    return strcmp(from, to) <= 0;
}

static cJSON *read_range(App *app, const char *sql, const char *from, const char *to, const char *search) {
    sqlite3_stmt *stmt = db_prepare(app, sql);
    if (!stmt) return NULL;
    bind_text(stmt, 1, from);
    bind_text(stmt, 2, to);
    if (search) bind_text(stmt, 3, search);
    return read_rows(stmt);
}

static Response get_sales(App *app, const Request *req) {
    char from[11], to[11], search[121];
    if (!date_filters(req, from, to) || query_param(req->query, "search", search, sizeof(search)) < 0)
        return error_response(400, "Informe um período válido, com a data inicial anterior ou igual à final.");
    cJSON *rows = read_range(app,
        "SELECT s.*, (SELECT sum(quantity) FROM sale_items WHERE sale_id=s.id) AS item_count "
        "FROM sales s WHERE date(s.created_at,'-3 hours') BETWEEN ?1 AND ?2 "
        "AND (?3='' OR instr(lower(s.customer),lower(?3))>0 OR CAST(s.id AS TEXT)=?3) "
        "ORDER BY s.created_at DESC,s.id DESC", from, to, search);
    return rows ? json_response(200, rows) : db_error();
}

static Response get_sale(App *app, int64_t id) {
    cJSON *rows = read_rows_by_id(app, "SELECT * FROM sales WHERE id=?", id);
    if (!rows) return db_error();
    cJSON *sale = take_first_row(rows);
    if (!sale) return error_response(404, "Venda não encontrada.");
    cJSON *items = read_rows_by_id(app, "SELECT * FROM sale_items WHERE sale_id=? ORDER BY id", id);
    if (!items || !cJSON_AddItemToObject(sale, "items", items)) {
        cJSON_Delete(items);
        cJSON_Delete(sale);
        return db_error();
    }
    return json_response(200, sale);
}

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

static Response create_sale(App *app, const cJSON *json) {
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

static Response get_report(App *app, const Request *req) {
    char from[11], to[11];
    if (!date_filters(req, from, to)) return error_response(400, "Período inválido. Confira as datas inicial e final.");
    cJSON *summary = take_first_row(read_range(app,
        "SELECT count(*) AS sale_count, coalesce(sum(total_cents),0) AS total_cents "
        "FROM sales WHERE status='completed' AND date(created_at,'-3 hours') BETWEEN ?1 AND ?2",
        from, to, NULL));
    cJSON *report = cJSON_CreateObject();
    if (!report || !summary ||
        !cJSON_AddStringToObject(report, "from", from) || !cJSON_AddStringToObject(report, "to", to) ||
        !cJSON_AddItemToObject(report, "summary", summary)) {
        cJSON_Delete(summary);
        cJSON_Delete(report);
        return db_error();
    }
    return json_response(200, report);
}

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
