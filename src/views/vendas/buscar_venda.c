#include "views.h"

Response get_sale(App *app, int64_t id) {
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
