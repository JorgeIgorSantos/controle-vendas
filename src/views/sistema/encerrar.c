#include "views.h"

Response shutdown_server(void) {
    cJSON *json = cJSON_CreateObject();
    if (json) cJSON_AddStringToObject(json, "message", "Servidor encerrado. Dados preservados.");
    Response response = json_response(200, json);
    if (response.body) http_stop();
    return response;
}
