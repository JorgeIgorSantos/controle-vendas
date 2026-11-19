#include "views.h"

Response get_sales(App *app, const Request *req) {
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
