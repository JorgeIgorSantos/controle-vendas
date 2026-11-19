#ifndef VENDA_VIEWS_H
#define VENDA_VIEWS_H

#include "http.h"

Response get_products(App *app, const Request *req);
Response get_product(App *app, int64_t id);
Response save_product(App *app, const cJSON *json, int64_t id);
Response delete_product(App *app, int64_t id);

Response get_sales(App *app, const Request *req);
Response get_sale(App *app, int64_t id);
Response create_sale(App *app, const cJSON *json);

Response get_report(App *app, const Request *req);

Response get_health(void);
Response shutdown_server(void);

#endif
