#!/usr/bin/env bash

set -euo pipefail

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

case "$#" in
    0)
        cd /tmp/
        git clone https://github.com/Nighty3098/SkyFall --recurse-submodules
        cd SkyFall
        python3 setup.py
        cd ~/
        clear
        banner
        echo -e "\033[0;32mSuccessfully installed\033[0m"
        ;;
    1)
        ;;
    *)
        echo "Error"
        ;;
esac

