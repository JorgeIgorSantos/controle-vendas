#ifndef VENDA_API_HELPERS_H
#define VENDA_API_HELPERS_H

#include "app.h"

Response db_error(void);
/* Consome e finaliza o statement; quem recebe as linhas deve liberá-las. */
cJSON *read_rows(sqlite3_stmt *stmt);
void bind_text(sqlite3_stmt *stmt, int index, const char *value);
cJSON *read_rows_by_id(App *app, const char *sql, int64_t id);
/* Consome o array e transfere a primeira linha para quem chamou. */
cJSON *take_first_row(cJSON *rows);
int date_filters(const Request *req, char *from, char *to);
cJSON *read_range(App *app, const char *sql, const char *from, const char *to, const char *search);

#endif
