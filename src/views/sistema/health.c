#include "app.h"

Response get_health(void) {
    cJSON *json = cJSON_CreateObject();
    if (json) { cJSON_AddStringToObject(json, "status", "ok"); cJSON_AddStringToObject(json, "version", APP_VERSION); }
    return json_response(200, json);
}
