#include "views.h"
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
