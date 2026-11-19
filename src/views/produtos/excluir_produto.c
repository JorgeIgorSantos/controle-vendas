#include "views.h"

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
