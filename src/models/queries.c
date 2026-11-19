#include "models.h"
#include <string.h>

/* Consome e finaliza o statement depois de converter o resultado. */
cJSON *read_rows(sqlite3_stmt *stmt) {
    cJSON *rows = cJSON_CreateArray();
    int rc = SQLITE_NOMEM;
    while (rows && (rc = sqlite3_step(stmt)) == SQLITE_ROW) {
        cJSON *row = cJSON_CreateObject();
        if (!row) break;
        for (int i = 0; i < sqlite3_column_count(stmt); i++) {
            const char *name = sqlite3_column_name(stmt, i);
            switch (sqlite3_column_type(stmt, i)) {
                case SQLITE_INTEGER:
                    if (!strcmp(name, "active")) cJSON_AddBoolToObject(row, name, sqlite3_column_int(stmt, i));
                    else cJSON_AddNumberToObject(row, name, (double)sqlite3_column_int64(stmt, i));
                    break;
                case SQLITE_FLOAT: cJSON_AddNumberToObject(row, name, sqlite3_column_double(stmt, i)); break;
                case SQLITE_NULL: cJSON_AddNullToObject(row, name); break;
                default: cJSON_AddStringToObject(row, name, (const char *)sqlite3_column_text(stmt, i));
            }
        }
        if (!cJSON_AddItemToArray(rows, row)) {
            cJSON_Delete(row);
            break;
        }
    }
    sqlite3_finalize(stmt);
    if (rc == SQLITE_DONE) return rows;
    cJSON_Delete(rows);
    return NULL;
}

void bind_text(sqlite3_stmt *stmt, int index, const char *value) {
    sqlite3_bind_text(stmt, index, value, -1, SQLITE_TRANSIENT);
}

cJSON *read_rows_by_id(App *app, const char *sql, int64_t id) {
    sqlite3_stmt *stmt = db_prepare(app, sql);
    if (!stmt) return NULL;
    sqlite3_bind_int64(stmt, 1, id);
    return read_rows(stmt);
}

cJSON *take_first_row(cJSON *rows) {
    cJSON *row = cJSON_DetachItemFromArray(rows, 0);
    cJSON_Delete(rows);
    return row;
}

cJSON *read_range(App *app, const char *sql, const char *from, const char *to, const char *search) {
    sqlite3_stmt *stmt = db_prepare(app, sql);
    if (!stmt) return NULL;
    bind_text(stmt, 1, from);
    bind_text(stmt, 2, to);
    if (search) bind_text(stmt, 3, search);
    return read_rows(stmt);
}
