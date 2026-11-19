#ifndef VENDA_SALES_H
#define VENDA_SALES_H

#include "app.h"

Response get_sales(App *app, const Request *req);
Response get_sale(App *app, int64_t id);
Response create_sale(App *app, const cJSON *json);

#endif
