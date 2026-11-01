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
    printf '\033[0m'
}

main() {
    INSTALL_DIR="$(mktemp -d "${TMPDIR:-/tmp}/skyfall-install.XXXXXX")"
    trap cleanup EXIT

    git clone --recurse-submodules https://github.com/Nighty3098/SkyFall "$INSTALL_DIR/SkyFall"
    cd "$INSTALL_DIR/SkyFall"

    python3 setup.py "$@"

    if [ -t 1 ] && command -v clear >/dev/null 2>&1; then
        clear
    fi
    banner
    printf '\033[0;32mSuccessfully installed\033[0m\n'
}

main "$@"
