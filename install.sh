#!/usr/bin/env bash

set -euo pipefail

cleanup() {
    if [ -n "${INSTALL_DIR:-}" ]; then
        rm -rf "$INSTALL_DIR"
    fi
}

banner() {
    printf '\033[1;36m'
    cat <<'EOF'
  _____ __  _  __ __  _____   ____  _      _
 / ___/|  l/ ]|  T  T|     | /    T| T    | T
(   \_ |  ' / |  |  ||   __jY  o  || |    | |
 \__  T|    \ |  ~  ||  l_  |     || l___ | l___
 /  \ ||     Yl___, ||   _] |  _  ||     T|     T
 \    ||  .  ||     !|  T   |  |  ||     ||     |
  \___jl__j\_jl____/ l__j   l__j__jl_____jl_____j
EOF
    printf '\033[0m\n'
}

step() {
    printf '\033[1;36m›\033[0m %s\n' "$*"
}

main() {
    INSTALL_DIR="$(mktemp -d "${TMPDIR:-/tmp}/skyfall-install.XXXXXX")"
    trap cleanup EXIT

    banner
    printf '\n'

    uninstall_mode=0
    for arg in "$@"; do
        case "$arg" in
            --uninstall|uninstall) uninstall_mode=1 ;;
        esac
    done

    if ! command -v git >/dev/null 2>&1; then
        printf 'Error: git is required. Install git and run this script again.\n' >&2
        return 1
    fi

    step 'Downloading SkyFall...'
    if ! git clone --quiet --depth 1 --recurse-submodules --shallow-submodules \
        https://github.com/Nighty3098/SkyFall "$INSTALL_DIR/SkyFall" \
        >"$INSTALL_DIR/clone.log" 2>&1; then
        printf 'Error: could not download SkyFall.\n' >&2
        tail -n 30 "$INSTALL_DIR/clone.log" >&2
        return 1
    fi

    if [ "$uninstall_mode" -eq 1 ]; then
        step 'Starting uninstaller...'
    else
        step 'Starting installer...'
    fi
    printf '\n'
    cd "$INSTALL_DIR/SkyFall"

    python3 setup.py "$@"
}

main "$@"
