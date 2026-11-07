CC ?= cc
CPPFLAGS = -Iinclude -Ivendor/sqlite -Ivendor/cjson -D_POSIX_C_SOURCE=200809L
CFLAGS ?= -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror
LDLIBS = -lm -lpthread -ldl
BUILD_DIR ?= build
WEB_FILES = $(if $(wildcard web/src),$(shell find web/src)) web/angular.json web/tsconfig.json web/package.json web/package-lock.json
SOURCES = src/main.c src/http.c src/database.c src/utils.c src/api.c
OBJECTS = $(patsubst src/%.c,$(BUILD_DIR)/%.o,$(SOURCES))

.PHONY: all backend run test clean sanitize package
all: backend web/dist/browser/index.html
backend: $(BUILD_DIR)/vendas
web/node_modules/.package-lock.json: web/package.json web/package-lock.json
	npm --prefix web ci --include=dev
web/dist/browser/index.html: $(WEB_FILES) web/node_modules/.package-lock.json
	npm --prefix web run build
$(BUILD_DIR):
	mkdir -p $(BUILD_DIR) data
$(BUILD_DIR)/%.o: src/%.c include/app.h | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@
$(BUILD_DIR)/sqlite3.o: vendor/sqlite/sqlite3.c vendor/sqlite/sqlite3.h | $(BUILD_DIR)
	$(CC) -std=c11 -O2 -DSQLITE_THREADSAFE=1 -DSQLITE_DQS=0 -DSQLITE_OMIT_LOAD_EXTENSION -c $< -o $@
$(BUILD_DIR)/cJSON.o: vendor/cjson/cJSON.c vendor/cjson/cJSON.h | $(BUILD_DIR)
	$(CC) -std=c11 -O2 -c $< -o $@
$(BUILD_DIR)/vendas: $(OBJECTS) $(BUILD_DIR)/sqlite3.o $(BUILD_DIR)/cJSON.o
	$(CC) $(CFLAGS) $^ $(LDLIBS) -o $@
run: all
	./$(BUILD_DIR)/vendas
test: all
	python3 tests/test_api.py
sanitize:
	$(MAKE) BUILD_DIR=build/sanitized CFLAGS='-std=c11 -g -O1 -Wall -Wextra -Wpedantic -Werror -fsanitize=address,undefined -fno-omit-frame-pointer'
	ASAN_OPTIONS=detect_leaks=1 VENDA_BINARY=build/sanitized/vendas python3 tests/test_api.py
package:
	python3 scripts/package.py
clean:
	rm -f $(BUILD_DIR)/*.o $(BUILD_DIR)/vendas
	rm -rf web/dist
