#!/bin/sh
# Распаковывает engines-binaries.tar.gz (вендоренные .so/.dll/.h CPLEX/ALGLIB/
# QORE, не хранятся в git — см. корневой .gitignore) в клон репозитория.
# Запускать на сервере рядом с архивом и папкой репозитория:
#   ./unpack-engines.sh [путь-к-архиву] [путь-к-репозиторию]
# По умолчанию: ./engines-binaries.tar.gz -> ./solver_arena

set -e

ARCHIVE="${1:-engines-binaries.tar.gz}"
REPO_DIR="${2:-solver_arena}"

if [ ! -f "$ARCHIVE" ]; then
    echo "Не найден архив: $ARCHIVE" >&2
    exit 1
fi

if [ ! -d "$REPO_DIR" ]; then
    echo "Не найдена папка репозитория: $REPO_DIR" >&2
    exit 1
fi

tar -xzf "$ARCHIVE" -C "$REPO_DIR"

echo "Распаковано в $REPO_DIR. Проверка:"
for f in \
    backend/engines/alglib/alglib408_64free.so \
    backend/engines/cplex/libcplex1261.so \
    backend/engines/qore/qore_opt_py.cpython-38-x86_64-linux-gnu.so
do
    if [ -f "$REPO_DIR/$f" ]; then
        echo "  OK  $f"
    else
        echo "  НЕТ $f" >&2
    fi
done

rm "$ARCHIVE"
echo "Архив удалён: $ARCHIVE"
