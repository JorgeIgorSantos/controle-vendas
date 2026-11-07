#include "app.h"
#include <stdio.h>

int db_exec(App *app, const char *sql) {
    if (sqlite3_exec(app->db, sql, NULL, NULL, NULL) == SQLITE_OK) return 1;
    fprintf(stderr, "Banco: %s\n", sqlite3_errmsg(app->db));
    return 0;
}

sqlite3_stmt *db_prepare(App *app, const char *sql) {
    sqlite3_stmt *stmt;
    if (sqlite3_prepare_v2(app->db, sql, -1, &stmt, NULL) == SQLITE_OK) return stmt;
    fprintf(stderr, "Consulta: %s\n", sqlite3_errmsg(app->db));
    return NULL;
}

int db_open(App *app, const char *path) {
    if (sqlite3_open(path, &app->db) != SQLITE_OK) {
        fprintf(stderr, "Não foi possível abrir o banco: %s\n", sqlite3_errmsg(app->db));
        return 0;
    }
    sqlite3_busy_timeout(app->db, 5000);
    /* As colunas antigas preservam os bancos e o histórico já gravado. */
    return db_exec(app,
        "PRAGMA foreign_keys=ON; PRAGMA journal_mode=WAL;"
        "CREATE TABLE IF NOT EXISTS products ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "sku TEXT NOT NULL COLLATE NOCASE UNIQUE CHECK(length(trim(sku)) BETWEEN 1 AND 40),"
        "name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 120),"
        "category TEXT NOT NULL CHECK(length(trim(category)) BETWEEN 1 AND 60),"
        "price_cents INTEGER NOT NULL CHECK(price_cents BETWEEN 1 AND 100000000),"
        "stock INTEGER NOT NULL CHECK(stock BETWEEN 0 AND 1000000),"
        "min_stock INTEGER NOT NULL CHECK(min_stock BETWEEN 0 AND 1000000),"
        "active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),"
        "notes TEXT NOT NULL DEFAULT '',"
        "created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),"
        "updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')));"
        "CREATE TABLE IF NOT EXISTS sales ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, customer TEXT NOT NULL DEFAULT '',"
        "payment_method TEXT NOT NULL CHECK(payment_method IN ('pix','dinheiro','credito','debito')),"
        "subtotal_cents INTEGER NOT NULL CHECK(subtotal_cents>0),"
        "discount_cents INTEGER NOT NULL CHECK(discount_cents>=0 AND discount_cents<=subtotal_cents),"
        "total_cents INTEGER NOT NULL CHECK(total_cents=subtotal_cents-discount_cents),"
        "status TEXT NOT NULL DEFAULT 'completed' CHECK(status IN ('completed','cancelled')),"
        "notes TEXT NOT NULL DEFAULT '',"
        "created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),"
        "cancelled_at TEXT);"
        "CREATE TABLE IF NOT EXISTS sale_items ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, sale_id INTEGER NOT NULL REFERENCES sales(id),"
        "product_id INTEGER NOT NULL REFERENCES products(id), sku TEXT NOT NULL, name TEXT NOT NULL,"
        "quantity INTEGER NOT NULL CHECK(quantity BETWEEN 1 AND 1000000),"
        "unit_price_cents INTEGER NOT NULL CHECK(unit_price_cents>0),"
        "total_cents INTEGER NOT NULL CHECK(total_cents=quantity*unit_price_cents),"
        "UNIQUE(sale_id,product_id));"
        "CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(created_at);"
        "CREATE INDEX IF NOT EXISTS idx_items_product ON sale_items(product_id);"
        "PRAGMA user_version=1;");
}
