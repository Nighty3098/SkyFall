<div align="center">

# `SkyFall Project`

<br /><br />

<img src="resources/banner.png" width="95%" />

<br /><br /><br /><br />

<img src="resources/img.png" width="95%" />

<br /><br />

</div>

## `SETUP SEARXNG`

To work with dorking, you need to run searxng via docker:

```bash

docker compose up --build

```

## `DOWNLOAD`

```bash

git clone https://github.com/Nighty3098/SkyFall --recurse-submodules

```

## `INSTALL (Linux)`

System-wide install like wifite2 — copies the app to `/opt/skyfall`,
creates the `skyfall` launcher, the app-menu entry and icons
(X11 + Wayland):

```bash

sudo python3 setup.py

# run it
skyfall

# update after git pull (just re-run)
git pull
sudo python3 setup.py

# uninstall
sudo python3 setup.py uninstall

```

Without root (installs to `~/.local`):

```bash

python3 setup.py --user

```

## `RUN (without install)`

```bash

python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt

python3 main.py

```

## `CONNECT MCP TO OPENCODE`

The project ships an MCP server exposing the OSINT tools. To use it from [opencode](https://opencode.ai):

1. **Start the server** — either run the GUI and click `Start MCP Server` in `SETTINGS`, or launch it standalone:

```bash
python3 src/skyfall_mcp_server.py --transport sse --host 127.0.0.1 --port 9877
```

2. **Configure opencode** — add the following to `opencode.json` in your project root (an identical config is already provided):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "skyfall": {
      "type": "remote",
      "url": "http://127.0.0.1:9877/sse",
      "enabled": true
    }
  }
}
```

3. Restart opencode and verify the server appears in `/mcp`.

## `DEVELOPMENT`

```bash

# Lint check
./check.sh

# Auto-format
./format.sh

```

## `CONTACTS`

Main Developer: https://t.me/Night3098

GitHub: https://github.com/Nighty3098

## `THIRDPARTY`

### TXFetch — Blockchain Transaction Search Engine

Blockchain transaction retrieval tool — find a transaction hash using only indirect data: time, amount, and network.

- **Author:** xaynov (https://github.com/xaynov-osint)
- **License:** [MIT](./thirdparty/txfetch/LICENSE)
- **Repository:** https://github.com/xaynov-osint/txfetch
- **Copyright:** Copyright (c) 2026 xaynov

## `GENERATE THIRD-PARTY NOTICES`

```bash

pip install pip-licenses
pip-licenses --with-authors --with-urls --format=markdown > THIRD_PARTY_NOTICES.md

```
