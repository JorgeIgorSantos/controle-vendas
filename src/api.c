#include "app.h"
#include <errno.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static Response db_error(void) { return error_response(500, "Não foi possível concluir a operação no banco de dados."); }

static cJSON *statement_rows(sqlite3_stmt *stmt) {
    cJSON *rows = cJSON_CreateArray();
    if (!rows) return NULL;
    int rc;
    while ((rc = sqlite3_step(stmt)) == SQLITE_ROW) {
        cJSON *row = cJSON_CreateObject();
        if (!row) { cJSON_Delete(rows); return NULL; }
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
        if (!cJSON_AddItemToArray(rows, row)) { cJSON_Delete(row); cJSON_Delete(rows); return NULL; }
    }
    if (rc != SQLITE_DONE) { cJSON_Delete(rows); return NULL; }
    return rows;
}

static int bind_text(sqlite3_stmt *stmt, int index, const char *value) {
    return sqlite3_bind_text(stmt, index, value, -1, SQLITE_TRANSIENT) == SQLITE_OK;
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
    sqlite3_stmt *stmt = NULL;
    if (!db_prepare(app, &stmt,
        "SELECT * FROM products WHERE (?1=-1 OR active=?1) AND "
        "(?2='' OR instr(lower(name),lower(?2))>0 OR instr(lower(sku),lower(?2))>0 "
        "OR instr(lower(category),lower(?2))>0) ORDER BY name COLLATE NOCASE,id")) return db_error();
    sqlite3_bind_int(stmt, 1, active);
    bind_text(stmt, 2, search);
    cJSON *rows = statement_rows(stmt);
    sqlite3_finalize(stmt);
    return rows ? json_response(200, rows) : db_error();
}

static Response get_product(App *app, int64_t id) {
    sqlite3_stmt *stmt = NULL;
    if (!db_prepare(app, &stmt, "SELECT * FROM products WHERE id=?")) return db_error();
    sqlite3_bind_int64(stmt, 1, id);
    cJSON *rows = statement_rows(stmt);
    sqlite3_finalize(stmt);
    if (!rows) return db_error();
    cJSON *product = cJSON_DetachItemFromArray(rows, 0);
    cJSON_Delete(rows);
    return product ? json_response(200, product) : error_response(404, "Produto não encontrado.");
}

static int parse_product(const cJSON *json, Product *product) {
    int64_t stock, minimum;
    const cJSON *active = cJSON_GetObjectItemCaseSensitive(json, "active");
    if (!json_text(json, "sku", product->sku, sizeof(product->sku), 1) ||
        !json_text(json, "name", product->name, sizeof(product->name), 1) ||
        !json_text(json, "category", product->category, sizeof(product->category), 1) ||
        !json_text(json, "notes", product->notes, sizeof(product->notes), 0) ||
        !json_integer(json, "price_cents", 1, MAX_PRICE_CENTS, &product->price_cents) ||
        !json_integer(json, "stock", 0, MAX_QUANTITY, &stock) ||
        !json_integer(json, "min_stock", 0, MAX_QUANTITY, &minimum) ||
        (active && !cJSON_IsBool(active))) return 0;
    product->stock = (int)stock;
    product->min_stock = (int)minimum;
    product->active = !active || cJSON_IsTrue(active);
    return 1;
}

static Response save_product(App *app, const cJSON *json, int64_t id) {
    Product product = {0};
    if (!parse_product(json, &product)) return error_response(400,
        "Informe código, nome, categoria, preço positivo em centavos e estoques inteiros entre 0 e 1.000.000. Respeite os limites dos campos.");
    sqlite3_stmt *stmt = NULL;
    const char *sql = id ?
        "UPDATE products SET sku=?1,name=?2,category=?3,price_cents=?4,stock=?5,min_stock=?6,active=?7,notes=?8,"
        "updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id=?9" :
        "INSERT INTO products(sku,name,category,price_cents,stock,min_stock,active,notes) VALUES(?1,?2,?3,?4,?5,?6,?7,?8)";
    if (!db_prepare(app, &stmt, sql)) return db_error();
    bind_text(stmt, 1, product.sku); bind_text(stmt, 2, product.name); bind_text(stmt, 3, product.category);
    sqlite3_bind_int64(stmt, 4, product.price_cents);
    sqlite3_bind_int(stmt, 5, product.stock); sqlite3_bind_int(stmt, 6, product.min_stock);
    sqlite3_bind_int(stmt, 7, product.active); bind_text(stmt, 8, product.notes);
    if (id) sqlite3_bind_int64(stmt, 9, id);
    int rc = sqlite3_step(stmt), changes = sqlite3_changes(app->db);
    sqlite3_finalize(stmt);
    if (rc == SQLITE_CONSTRAINT) return error_response(409, "Já existe um produto com este código. Use um código único.");
    if (rc != SQLITE_DONE) return db_error();
    if (id && !changes) return error_response(404, "Produto não encontrado.");
    Response response = get_product(app, id ? id : sqlite3_last_insert_rowid(app->db));
    if (!id && response.status == 200) response.status = 201;
    return response;
}

static Response delete_product(App *app, int64_t id) {
    sqlite3_stmt *stmt = NULL;
    if (!db_prepare(app, &stmt, "DELETE FROM products WHERE id=?")) return db_error();
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

static Response get_sales(App *app, const Request *req) {
    char from[11], to[11], search[121];
    if (!date_filters(req, from, to) || query_param(req->query, "search", search, sizeof(search)) < 0)
        return error_response(400, "Informe um período válido, com a data inicial anterior ou igual à final.");
    sqlite3_stmt *stmt = NULL;
    if (!db_prepare(app, &stmt,
        "SELECT s.*, (SELECT sum(quantity) FROM sale_items WHERE sale_id=s.id) AS item_count "
        "FROM sales s WHERE date(s.created_at,'-3 hours') BETWEEN ?1 AND ?2 "
        "AND (?3='' OR instr(lower(s.customer),lower(?3))>0 OR CAST(s.id AS TEXT)=?3) "
        "ORDER BY s.created_at DESC,s.id DESC")) return db_error();
    bind_text(stmt, 1, from); bind_text(stmt, 2, to); bind_text(stmt, 3, search);
    cJSON *rows = statement_rows(stmt);
    sqlite3_finalize(stmt);
    return rows ? json_response(200, rows) : db_error();
}

static Response get_sale(App *app, int64_t id) {
    sqlite3_stmt *stmt = NULL;
    if (!db_prepare(app, &stmt, "SELECT * FROM sales WHERE id=?")) return db_error();
    sqlite3_bind_int64(stmt, 1, id);
    cJSON *rows = statement_rows(stmt);
    sqlite3_finalize(stmt);
    if (!rows) return db_error();
    cJSON *sale = cJSON_DetachItemFromArray(rows, 0);
    cJSON_Delete(rows);
    if (!sale) return error_response(404, "Venda não encontrada.");
    if (!db_prepare(app, &stmt, "SELECT * FROM sale_items WHERE sale_id=? ORDER BY id")) {
        cJSON_Delete(sale); return db_error();
    }
    sqlite3_bind_int64(stmt, 1, id);
    cJSON *items = statement_rows(stmt);
    sqlite3_finalize(stmt);
    if (!items) { cJSON_Delete(sale); return db_error(); }
    cJSON_AddItemToObject(sale, "items", items);
    return json_response(200, sale);
}

static int payment_valid(const char *value) {
    return !strcmp(value, "pix") || !strcmp(value, "dinheiro") || !strcmp(value, "credito") || !strcmp(value, "debito");
}

static Response create_sale(App *app, const cJSON *json) {
    Sale sale = {0};
    cJSON *items = cJSON_GetObjectItemCaseSensitive(json, "items");
    int count = cJSON_GetArraySize(items);
    if (!json_text(json, "customer", sale.customer, sizeof(sale.customer), 0) ||
        !json_text(json, "payment_method", sale.payment_method, sizeof(sale.payment_method), 1) ||
        !payment_valid(sale.payment_method) ||
        !json_text(json, "notes", sale.notes, sizeof(sale.notes), 0) ||
        !json_integer(json, "discount_cents", 0, MAX_SALE_CENTS, &sale.discount_cents) ||
        !cJSON_IsArray(items) || count < 1 || count > MAX_ITEMS)
        return error_response(400, "Informe de 1 a 200 produtos, pagamento válido e desconto não negativo em centavos.");

    sale.item_count = (size_t)count;
    /* A quantidade de itens só é conhecida em execução; calloc é verificado e liberado em todas as saídas. */
    sale.items = calloc(sale.item_count, sizeof(*sale.items));
    if (!sale.items) return error_response(500, "Memória insuficiente para registrar a venda.");
    for (int i = 0; i < count; i++) {
        cJSON *item = cJSON_GetArrayItem(items, i);
        int64_t quantity;
        if (!cJSON_IsObject(item) || !json_integer(item, "product_id", 1, 2147483647, &sale.items[i].product_id) ||
            !json_integer(item, "quantity", 1, MAX_QUANTITY, &quantity)) {
            free(sale.items); return error_response(400, "Produto ou quantidade inválida. Use quantidades inteiras positivas.");
        }
        sale.items[i].quantity = (int)quantity;
        for (int j = 0; j < i; j++) if (sale.items[j].product_id == sale.items[i].product_id) {
            free(sale.items); return error_response(400, "Produto repetido na venda. Agrupe as quantidades no mesmo item.");
        }
    }
    if (!db_exec(app, "BEGIN IMMEDIATE")) { free(sale.items); return db_error(); }
    sqlite3_stmt *stmt = NULL;
    const char *failure = NULL;
    int status = 500;
    for (int i = 0; i < count; i++) {
        SaleItem *item = &sale.items[i];
        if (!db_prepare(app, &stmt, "SELECT sku,name,price_cents,stock,active FROM products WHERE id=?")) goto failed;
        sqlite3_bind_int64(stmt, 1, item->product_id);
        int rc = sqlite3_step(stmt);
        if (rc == SQLITE_DONE) { failure = "Um dos produtos não existe."; status = 404; goto failed; }
        if (rc != SQLITE_ROW) goto failed;
        if (!sqlite3_column_int(stmt, 4)) { failure = "Produto inativo não pode ser vendido."; status = 409; goto failed; }
        if (sqlite3_column_int(stmt, 3) < item->quantity) {
            failure = "Estoque insuficiente. Revise a quantidade dos itens."; status = 409; goto failed;
        }
        snprintf(item->sku, sizeof(item->sku), "%s", sqlite3_column_text(stmt, 0));
        snprintf(item->name, sizeof(item->name), "%s", sqlite3_column_text(stmt, 1));
        item->unit_price_cents = sqlite3_column_int64(stmt, 2);
        item->total_cents = item->unit_price_cents * item->quantity;
        sale.subtotal_cents += item->total_cents;
        sqlite3_finalize(stmt); stmt = NULL;
        if (sale.subtotal_cents > MAX_SALE_CENTS) { failure = "O valor da venda ultrapassa o limite permitido."; status = 400; goto failed; }
    }
    if (sale.discount_cents > sale.subtotal_cents) {
        failure = "O desconto não pode ser maior que o subtotal."; status = 400; goto failed;
    }
    sale.total_cents = sale.subtotal_cents - sale.discount_cents;
    if (!db_prepare(app, &stmt,
        "INSERT INTO sales(customer,payment_method,subtotal_cents,discount_cents,total_cents,notes) VALUES(?,?,?,?,?,?)")) goto failed;
    bind_text(stmt, 1, sale.customer); bind_text(stmt, 2, sale.payment_method);
    sqlite3_bind_int64(stmt, 3, sale.subtotal_cents); sqlite3_bind_int64(stmt, 4, sale.discount_cents);
    sqlite3_bind_int64(stmt, 5, sale.total_cents); bind_text(stmt, 6, sale.notes);
    if (sqlite3_step(stmt) != SQLITE_DONE) goto failed;
    sqlite3_finalize(stmt); stmt = NULL;
    sale.id = sqlite3_last_insert_rowid(app->db);
    for (int i = 0; i < count; i++) {
        SaleItem *item = &sale.items[i];
        if (!db_prepare(app, &stmt, "INSERT INTO sale_items(sale_id,product_id,sku,name,quantity,unit_price_cents,total_cents) VALUES(?,?,?,?,?,?,?)")) goto failed;
        sqlite3_bind_int64(stmt, 1, sale.id); sqlite3_bind_int64(stmt, 2, item->product_id);
        bind_text(stmt, 3, item->sku); bind_text(stmt, 4, item->name);
        sqlite3_bind_int(stmt, 5, item->quantity); sqlite3_bind_int64(stmt, 6, item->unit_price_cents);
        sqlite3_bind_int64(stmt, 7, item->total_cents);
        if (sqlite3_step(stmt) != SQLITE_DONE) goto failed;
        sqlite3_finalize(stmt); stmt = NULL;
        if (!db_prepare(app, &stmt,
            "UPDATE products SET stock=stock-?,updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id=? AND stock>=?")) goto failed;
        sqlite3_bind_int(stmt, 1, item->quantity); sqlite3_bind_int64(stmt, 2, item->product_id);
        sqlite3_bind_int(stmt, 3, item->quantity);
        if (sqlite3_step(stmt) != SQLITE_DONE || sqlite3_changes(app->db) != 1) goto failed;
        sqlite3_finalize(stmt); stmt = NULL;
    }
    if (!db_exec(app, "COMMIT")) goto failed;
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

static Response cancel_sale(App *app, int64_t id) {
    if (!db_exec(app, "BEGIN IMMEDIATE")) return db_error();
    sqlite3_stmt *stmt = NULL;
    const char *failure = NULL;
    int status = 500;
    if (!db_prepare(app, &stmt, "SELECT status FROM sales WHERE id=?")) goto failed;
    sqlite3_bind_int64(stmt, 1, id);
    int rc = sqlite3_step(stmt);
    if (rc == SQLITE_DONE) { failure = "Venda não encontrada."; status = 404; goto failed; }
    if (rc != SQLITE_ROW) goto failed;
    if (strcmp((const char *)sqlite3_column_text(stmt, 0), "completed") != 0) {
        failure = "Esta venda já foi cancelada."; status = 409; goto failed;
    }
    sqlite3_finalize(stmt); stmt = NULL;
    if (!db_prepare(app, &stmt,
        "SELECT 1 FROM sale_items i JOIN products p ON p.id=i.product_id WHERE i.sale_id=? AND p.stock+i.quantity>1000000")) goto failed;
    sqlite3_bind_int64(stmt, 1, id);
    rc = sqlite3_step(stmt);
    if (rc == SQLITE_ROW) { failure = "A devolução ultrapassaria o limite de estoque. Ajuste o estoque antes de cancelar."; status = 409; goto failed; }
    if (rc != SQLITE_DONE) goto failed;
    sqlite3_finalize(stmt); stmt = NULL;
    if (!db_prepare(app, &stmt,
        "UPDATE products SET stock=stock+(SELECT quantity FROM sale_items WHERE sale_id=?1 AND product_id=products.id),"
        "updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id IN (SELECT product_id FROM sale_items WHERE sale_id=?1)")) goto failed;
    sqlite3_bind_int64(stmt, 1, id);
    if (sqlite3_step(stmt) != SQLITE_DONE) goto failed;
    sqlite3_finalize(stmt); stmt = NULL;
    if (!db_prepare(app, &stmt, "UPDATE sales SET status='cancelled',cancelled_at=strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id=?")) goto failed;
    sqlite3_bind_int64(stmt, 1, id);
    if (sqlite3_step(stmt) != SQLITE_DONE) goto failed;
    sqlite3_finalize(stmt); stmt = NULL;
    if (!db_exec(app, "COMMIT")) goto failed;
    return get_sale(app, id);
failed:
    sqlite3_finalize(stmt);
    db_exec(app, "ROLLBACK");
    return failure ? error_response(status, failure) : db_error();
}

static cJSON *report_query(App *app, const char *sql, const char *from, const char *to) {
    sqlite3_stmt *stmt = NULL;
    if (!db_prepare(app, &stmt, sql)) return NULL;
    bind_text(stmt, 1, from); bind_text(stmt, 2, to);
    cJSON *rows = statement_rows(stmt);
    sqlite3_finalize(stmt);
    return rows;
}

static Response get_report(App *app, const Request *req) {
    char from[11], to[11];
    if (!date_filters(req, from, to)) return error_response(400, "Período inválido. Confira as datas inicial e final.");
    cJSON *result = cJSON_CreateObject();
    if (!result) return db_error();
    cJSON_AddStringToObject(result, "from", from); cJSON_AddStringToObject(result, "to", to);
    const char *queries[] = {
        "SELECT count(*) AS sale_count,coalesce(sum(total_cents),0) AS total_cents,"
        "coalesce(sum(subtotal_cents),0) AS subtotal_cents,coalesce(sum(discount_cents),0) AS discount_cents,"
        "coalesce(round(avg(total_cents)),0) AS average_cents,"
        "(SELECT coalesce(sum(i.quantity),0) FROM sale_items i JOIN sales x ON x.id=i.sale_id "
        "WHERE x.status='completed' AND date(x.created_at,'-3 hours') BETWEEN ?1 AND ?2) AS items_sold,"
        "(SELECT count(*) FROM products WHERE active=1) AS active_products,"
        "(SELECT count(*) FROM products WHERE active=1 AND stock<=min_stock) AS low_stock_count,"
        "(SELECT count(*) FROM sales WHERE status='cancelled' AND date(created_at,'-3 hours') BETWEEN ?1 AND ?2) AS cancelled_count "
        "FROM sales s WHERE s.status='completed' AND date(s.created_at,'-3 hours') BETWEEN ?1 AND ?2",
        "SELECT date(s.created_at,'-3 hours') AS day,sum(s.total_cents) AS total_cents,count(*) AS sale_count "
        "FROM sales s WHERE s.status='completed' AND date(s.created_at,'-3 hours') BETWEEN ?1 AND ?2 GROUP BY day ORDER BY day",
        "SELECT i.product_id,i.sku,i.name,sum(i.quantity) AS quantity,sum(i.total_cents) AS gross_cents "
        "FROM sale_items i JOIN sales s ON s.id=i.sale_id WHERE s.status='completed' "
        "AND date(s.created_at,'-3 hours') BETWEEN ?1 AND ?2 GROUP BY i.product_id,i.sku,i.name ORDER BY quantity DESC,gross_cents DESC LIMIT 10",
        "SELECT payment_method,count(*) AS sale_count,sum(total_cents) AS total_cents FROM sales s "
        "WHERE status='completed' AND date(s.created_at,'-3 hours') BETWEEN ?1 AND ?2 GROUP BY payment_method ORDER BY total_cents DESC",
        "SELECT id,sku,name,category,stock,min_stock FROM products WHERE active=1 AND stock<=min_stock ORDER BY stock,name",
        "SELECT s.*, (SELECT sum(quantity) FROM sale_items WHERE sale_id=s.id) AS item_count "
        "FROM sales s WHERE date(s.created_at,'-3 hours') BETWEEN ?1 AND ?2 ORDER BY s.created_at DESC,s.id DESC"
    };
    const char *keys[] = {"summary", "daily", "top_products", "payments", "low_stock", "sales"};
    for (int i = 0; i < 6; i++) {
        cJSON *rows = report_query(app, queries[i], from, to);
        if (!rows) { cJSON_Delete(result); return db_error(); }
        if (i == 0) {
            cJSON *summary = cJSON_DetachItemFromArray(rows, 0);
            cJSON_Delete(rows);
            if (!summary) { cJSON_Delete(result); return db_error(); }
            cJSON_AddItemToObject(result, keys[i], summary);
        } else cJSON_AddItemToObject(result, keys[i], rows);
    }
    return json_response(200, result);
}

static int64_t resource_id(const char *path, const char *prefix, const char **suffix) {
    size_t n = strlen(prefix);
    if (strncmp(path, prefix, n) != 0 || path[n] < '1' || path[n] > '9') return 0;
    errno = 0;
    char *end;
    long long id = strtoll(path + n, &end, 10);
    if (errno || id <= 0 || id > 2147483647) return 0;
    *suffix = end;
    return (int64_t)id;
}

Response api_route(App *app, const Request *req) {
    int get = strcmp(req->method, "GET") == 0;
    int post = strcmp(req->method, "POST") == 0;
    int put = strcmp(req->method, "PUT") == 0;
    int del = strcmp(req->method, "DELETE") == 0;
    if (!strcmp(req->path, "/api/shutdown") && post) {
        cJSON *json = cJSON_CreateObject();
        if (json) cJSON_AddStringToObject(json, "message", "Servidor encerrado. Dados preservados.");
        Response response = json_response(200, json);
        if (response.body) http_stop();
        return response;
    }
    if (!strcmp(req->path, "/api/health") && get) {
        cJSON *json = cJSON_CreateObject();
        if (json) { cJSON_AddStringToObject(json, "status", "ok"); cJSON_AddStringToObject(json, "version", APP_VERSION); }
        return json_response(200, json);
    }
    if (!strcmp(req->path, "/api/reports") && get) return get_report(app, req);
    const char *suffix = "";
    int64_t product_id = resource_id(req->path, "/api/products/", &suffix);
    if (product_id && *suffix) product_id = 0;
    int64_t sale_id = resource_id(req->path, "/api/sales/", &suffix);
    int cancel = sale_id && !strcmp(suffix, "/cancel");
    if (sale_id && *suffix && !cancel) sale_id = 0;
    if (!strcmp(req->path, "/api/products") && get) return get_products(app, req);
    if (!strcmp(req->path, "/api/sales") && get) return get_sales(app, req);
    if (product_id && get) return get_product(app, product_id);
    if (product_id && del) return delete_product(app, product_id);
    if (sale_id && !cancel && get) return get_sale(app, sale_id);
    if (cancel && post) return cancel_sale(app, sale_id);
    int create_product = !strcmp(req->path, "/api/products") && post;
    int create = !strcmp(req->path, "/api/sales") && post;
    if (create_product || create || (product_id && put)) {
        cJSON *json = req->body ? cJSON_ParseWithOpts(req->body, NULL, 1) : NULL;
        if (!cJSON_IsObject(json)) { cJSON_Delete(json); return error_response(400, "Envie um objeto JSON válido."); }
        Response response = create ? create_sale(app, json) : save_product(app, json, product_id);
        cJSON_Delete(json);
        return response;
    }
    if (product_id || sale_id || !strcmp(req->path, "/api/products") || !strcmp(req->path, "/api/sales") ||
        !strcmp(req->path, "/api/reports") || !strcmp(req->path, "/api/health"))
        return error_response(405, "Operação não permitida para este recurso.");
    return error_response(404, "Recurso não encontrado.");
}
