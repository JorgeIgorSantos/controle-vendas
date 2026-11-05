#include "app.h"
#include <stdio.h>

int db_exec(App *app, const char *sql) {
    char *error = NULL;
    int rc = sqlite3_exec(app->db, sql, NULL, NULL, &error);
    if (rc != SQLITE_OK) {
        fprintf(stderr, "Banco: %s\n", error ? error : sqlite3_errmsg(app->db));
        sqlite3_free(error);
        return 0;
    }
    return 1;
}

int db_prepare(App *app, sqlite3_stmt **stmt, const char *sql) {
    if (sqlite3_prepare_v2(app->db, sql, -1, stmt, NULL) != SQLITE_OK) {
        fprintf(stderr, "Consulta: %s\n", sqlite3_errmsg(app->db));
        return 0;
    }
    return 1;
}

int db_open(App *app, const char *path) {
    if (sqlite3_open(path, &app->db) != SQLITE_OK) {
        fprintf(stderr, "Não foi possível abrir o banco: %s\n", sqlite3_errmsg(app->db));
        return 0;
    }
    sqlite3_busy_timeout(app->db, 5000);
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

/* A demonstração é opcional e só é criada em um banco sem produtos e vendas. */
int db_seed(App *app) {
    sqlite3_stmt *stmt = NULL;
    if (!db_prepare(app, &stmt, "SELECT (SELECT count(*) FROM products)+(SELECT count(*) FROM sales)")) return 0;
    int empty = sqlite3_step(stmt) == SQLITE_ROW && sqlite3_column_int(stmt, 0) == 0;
    sqlite3_finalize(stmt);
    if (!empty) return 1;
    return db_exec(app,
        "BEGIN IMMEDIATE;"
        "INSERT INTO products(sku,name,category,price_cents,stock,min_stock) VALUES"
        "('CAF-001','Café especial 250 g','Mercearia',2490,48,10),"
        "('CAN-002','Caneca de cerâmica','Casa e decoração',3990,24,5),"
        "('CAD-003','Caderno pontilhado','Papelaria',3290,35,8),"
        "('CHA-004','Chá de camomila','Mercearia',1590,7,10),"
        "('GAR-005','Garrafa térmica 500 ml','Utilidades',8990,18,5),"
        "('VEL-006','Vela aromática','Casa e decoração',4590,4,5),"
        "('ECO-007','Ecobag de algodão','Acessórios',2990,30,8),"
        "('LAP-008','Kit lápis grafite','Papelaria',1290,42,10);"
        "INSERT INTO sales(customer,payment_method,subtotal_cents,discount_cents,total_cents,created_at) VALUES"
        "('Ana Silva','pix',6480,0,6480,strftime('%Y-%m-%dT14:30:00Z','now','-6 days')),"
        "('Bruno Costa','credito',8990,500,8490,strftime('%Y-%m-%dT16:10:00Z','now','-5 days')),"
        "('Cliente balcão','dinheiro',6580,0,6580,strftime('%Y-%m-%dT13:20:00Z','now','-3 days')),"
        "('Carla Souza','debito',9570,0,9570,strftime('%Y-%m-%dT15:45:00Z','now','-2 days')),"
        "('Daniel Lima','pix',7470,0,7470,strftime('%Y-%m-%dT12:00:00Z','now','-1 day')),"
        "('Elisa Santos','credito',11970,970,11000,strftime('%Y-%m-%dT11:15:00Z','now'));"
        "INSERT INTO sale_items(sale_id,product_id,sku,name,quantity,unit_price_cents,total_cents) VALUES"
        "(1,1,'CAF-001','Café especial 250 g',1,2490,2490),"
        "(1,2,'CAN-002','Caneca de cerâmica',1,3990,3990),"
        "(2,5,'GAR-005','Garrafa térmica 500 ml',1,8990,8990),"
        "(3,3,'CAD-003','Caderno pontilhado',2,3290,6580),"
        "(4,2,'CAN-002','Caneca de cerâmica',2,3990,7980),"
        "(4,4,'CHA-004','Chá de camomila',1,1590,1590),"
        "(5,1,'CAF-001','Café especial 250 g',3,2490,7470),"
        "(6,2,'CAN-002','Caneca de cerâmica',3,3990,11970);"
        "UPDATE products SET stock=stock-(SELECT coalesce(sum(quantity),0) FROM sale_items WHERE product_id=products.id);"
        "COMMIT;");
}

void db_close(App *app) {
    if (app->db) sqlite3_close(app->db);
    app->db = NULL;
}
