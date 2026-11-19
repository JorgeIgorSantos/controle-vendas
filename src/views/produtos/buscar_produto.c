#include "views.h"

Response get_product(App *app, int64_t id) {
    cJSON *rows = read_rows_by_id(app, "SELECT * FROM products WHERE id=?", id);
    if (!rows) return db_error();
    cJSON *product = take_first_row(rows);
    return product ? json_response(200, product) : error_response(404, "Produto não encontrado.");
}
