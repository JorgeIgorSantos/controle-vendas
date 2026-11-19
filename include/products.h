#ifndef VENDA_PRODUCTS_H
#define VENDA_PRODUCTS_H

#include "app.h"

Response get_products(App *app, const Request *req);
Response get_product(App *app, int64_t id);
Response save_product(App *app, const cJSON *json, int64_t id);
Response delete_product(App *app, int64_t id);

#endif
