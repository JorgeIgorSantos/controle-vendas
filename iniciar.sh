#!/bin/sh
set -eu
cd "$(dirname "$0")"
make
printf '\nAbra http://127.0.0.1:8080 no navegador.\n\n'
exec ./build/vendas "$@"
