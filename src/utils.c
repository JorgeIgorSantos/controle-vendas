#include "app.h"
#include <ctype.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

Response json_response(int status, cJSON *json) {
    char *body = json ? cJSON_PrintUnformatted(json) : NULL;
    cJSON_Delete(json);
    if (!body) return (Response){500, NULL};
    return (Response){status, body};
}

Response error_response(int status, const char *message) {
    cJSON *json = cJSON_CreateObject();
    if (json) cJSON_AddStringToObject(json, "error", message);
    return json_response(status, json);
}

int json_integer(const cJSON *object, const char *key, int64_t min, int64_t max, int64_t *out) {
    const cJSON *value = cJSON_GetObjectItemCaseSensitive(object, key);
    if (!cJSON_IsNumber(value) || !isfinite(value->valuedouble) ||
        value->valuedouble < (double)min || value->valuedouble > (double)max ||
        floor(value->valuedouble) != value->valuedouble) return 0;
    *out = (int64_t)value->valuedouble;
    return 1;
}

int json_text(const cJSON *object, const char *key, char *out, size_t capacity, int required) {
    const cJSON *value = cJSON_GetObjectItemCaseSensitive(object, key);
    if (!value && !required) { out[0] = '\0'; return 1; }
    if (!cJSON_IsString(value)) return 0;
    const char *start = value->valuestring;
    while (*start && isspace((unsigned char)*start)) start++;
    size_t length = strlen(start);
    while (length && isspace((unsigned char)start[length - 1])) length--;
    if ((required && !length) || length >= capacity) return 0;
    for (size_t i = 0; i < length; i++) {
        if ((unsigned char)start[i] < 32 && start[i] != '\n' && start[i] != '\t') return 0;
    }
    memcpy(out, start, length);
    out[length] = '\0';
    return 1;
}

static int hex_value(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

int query_param(const char *query, const char *key, char *out, size_t capacity) {
    size_t key_len = strlen(key);
    out[0] = '\0';
    while (*query) {
        const char *end = strchr(query, '&');
        if (!end) end = query + strlen(query);
        const char *eq = memchr(query, '=', (size_t)(end - query));
        if (eq && (size_t)(eq - query) == key_len && strncmp(query, key, key_len) == 0) {
            size_t n = 0;
            for (const char *p = eq + 1; p < end; p++) {
                int c = (unsigned char)*p;
                if (c == '%') {
                    if (p + 2 >= end) return -1;
                    int hi = hex_value(p[1]), lo = hex_value(p[2]);
                    if (hi < 0 || lo < 0) return -1;
                    c = hi * 16 + lo;
                    p += 2;
                } else if (c == '+') c = ' ';
                if (!c || n + 1 >= capacity) return -1;
                out[n++] = (char)c;
            }
            out[n] = '\0';
            return 1;
        }
        query = *end ? end + 1 : end;
    }
    return 0;
}

int valid_date(const char *s) {
    if (strlen(s) != 10 || s[4] != '-' || s[7] != '-') return 0;
    for (int i = 0; i < 10; i++) if (i != 4 && i != 7 && !isdigit((unsigned char)s[i])) return 0;
    int y, m, d;
    if (sscanf(s, "%d-%d-%d", &y, &m, &d) != 3 || y < 1900 || y > 9999 || m < 1 || m > 12) return 0;
    int days[] = {31,28,31,30,31,30,31,31,30,31,30,31};
    if (y % 4 == 0 && (y % 100 != 0 || y % 400 == 0)) days[1] = 29;
    return d >= 1 && d <= days[m - 1];
}
