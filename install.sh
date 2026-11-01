#!/usr/bin/env bash

set -euo pipefail

cleanup() {
    if [ -n "${INSTALL_DIR:-}" ]; then
        rm -rf "$INSTALL_DIR"
    fi
}

run_stage() {
    local label="$1"
    local output="$INSTALL_DIR/stage.log"
    local frames='|/-\'
    local frame=0
    local pid
    shift

    printf '%s\n' "$label"
    "$@" >"$output" 2>&1 &
    pid=$!

    if [ -t 1 ]; then
        while kill -0 "$pid" 2>/dev/null; do
            printf '\r  %s' "${frames:frame++%${#frames}:1}"
            sleep 0.1
        done
    fi

    if wait "$pid"; then
        if [ -t 1 ]; then
            printf '\r  \033[0;32m✓\033[0m\n'
        else
            printf '  Готово\n'
        fi
    else
        local status=$?
        printf '\r  \033[0;31mОшибка (код %s)\033[0m\n' "$status" >&2
        tail -n 30 "$output" >&2
        return "$status"
    fi
}

main() {
    INSTALL_DIR="$(mktemp -d "${TMPDIR:-/tmp}/skyfall-install.XXXXXX")"
    trap cleanup EXIT

    run_stage "Загрузка SkyFall" \
        git clone --recurse-submodules https://github.com/Nighty3098/SkyFall "$INSTALL_DIR/SkyFall"
    cd "$INSTALL_DIR/SkyFall"

    run_stage "Установка и настройка" python3 setup.py "$@"

    printf '\033[0;32mУстановка завершена успешно\033[0m\n'
}

main "$@"
