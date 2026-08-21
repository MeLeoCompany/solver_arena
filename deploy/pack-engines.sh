#!/bin/sh
# Собирает архив с вендоренными бинарниками солверов (.so/.dll/.h под
# backend/engines/ — CPLEX/ALGLIB/QORE), которые не хранятся в git (см.
# корневой .gitignore) и должны доставляться на сервер отдельно.
# Запускать из корня репозитория (или откуда угодно — сам туда перейдёт):
#   ./deploy/pack-engines.sh [имя-архива]
# По умолчанию: engines-binaries.tar.gz в корне репозитория.

set -e

cd "$(dirname "$0")/.."

OUTPUT="${1:-engines-binaries.tar.gz}"

FILES=$(find backend/engines -type f \( -name '*.so' -o -name '*.dll' -o -name '*.h' \))

if [ -z "$FILES" ]; then
    echo "Не найдено бинарников под backend/engines/ (.so/.dll/.h) — нечего паковать" >&2
    exit 1
fi

echo "$FILES" | tar -czf "$OUTPUT" -T -

echo "Архив создан: $OUTPUT"
echo "Содержимое:"
tar -tzf "$OUTPUT"
