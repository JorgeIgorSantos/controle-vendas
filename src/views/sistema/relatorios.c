#include "views.h"

Response get_report(App *app, const Request *req) {
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
