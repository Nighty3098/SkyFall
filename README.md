<div align="center">

# `SkyFall Project`

<br /><br />

<img src="./resources/banner.png" width="95%" />

<br /><br /><br /><br />

<img src="./resources/img.png" width="95%" />

<br /><br />

</div>

## `FUNCTIONAL`

- [x] Collecting all information about web resources or ip addresses
  - [x] IP info (ipapi.co, ip-api.com, ipinfo.io)
  - [x] SSL / TLS (version, cipher, issuer, subject, expiry)
  - [x] DNS (A, MX, TXT, NS, CNAME, SOA with NS_IP resolution)
  - [x] Headers
  - [x] Server Location
  - [x] Associated Hosts (www, mail, dev, api, test subdomains)
  - [x] Open ports (nmap scan 1–65535)
  - [x] WHOIS (registrar, creation/expiration dates, name servers)
  - [x] Web stack (HTTP headers, web server, WAF, detected tech — Nginx, Apache, WordPress, Bitrix, jQuery)
  - [x] WAF (Cloudflare, Sucuri detection)
  - [x] Malware reputation (VirusTotal, Google Safe Browsing, CRDF Labs)
  - [x] NMAP (vuln scripts)
  - [x] robots.txt fetching
  - [x] security.txt (/.well-known/security.txt)
  - [x] Subdomain discovery via DuckDuckGo dorking
  - [x] Cookies analysis (extraction with attributes)
  - [x] Social tags (Open Graph, Twitter Cards)
- [x] Dorking via DuckDuckGo / SearXNG
  - [x] 7974 dorks from Exploit-DB GHDB, organized by categories
  - [x] Custom dork input and editing (right-click context menu)
  - [x] Result text search with highlighting
- [x] Telegram OSINT
  - [x] Multi-account support (auto-rotation of session files)
  - [x] Proxy support (SOCKS4/5, HTTP, MTProto — auto-testing and rotation)
  - [x] Flood-wait handling with exponential backoff
  - [x] User Data Collection
    - [x] Complete user profiles: ID, username, first name, last name, phone (if available)
    - [x] Statuses and flags: verification, Telegram Premium, bots, scam/fake accounts
    - [x] Activity: online/offline status, last seen timestamp
    - [x] Additional information: bio, language, profile photo
    - [x] Relationships: mutual contacts, presence in your contacts
  - [x] Channel Members Collection
    - [x] Retrieval of all channel/group members
    - [x] Saving membership data (join date, status)
    - [x] Integration with global user database
    - [x] Incremental sync support
  - [x] Avatar Download (separate profile photo download)
  - [x] Media Download (photos, videos, audio, documents with concurrency)
  - [ ] Automatic extraction and saving of file metadata to DB (MIME, size, dimensions, duration)
  - [x] Link Extraction
    - [x] Automatic extraction of all URLs from messages
    - [x] Support for Telegram links (t.me, @username)
    - [x] Saving link context (surrounding text)
    - [x] Link classification by type (telegram, http, https)
  - [x] Interaction Graph Analysis
    - [x] Build interaction graphs from collected data
    - [x] Nodes: users, channels, domains
    - [x] Edges: membership, replies, forwards, link mentions
    - [x] Discussion reply analysis (post-author and discussion chain replies)
    - [x] Cross-channel member analysis (shared members)
    - [x] Filter by date, minimum reply count, forwarded messages, link inclusion
    - [x] Graph statistics (node/edge types, degrees, bot/verified/premium counts)
  - [x] Graph export formats: GraphML, GEXF, JSON, CSV, PNG, HTML (pyvis.js interactive), Obsidian Markdown ([[wikilinks]])
  - [ ] Search and save to DB: cryptocurrency wallets (BTC, ETH, etc.) and phone numbers from messages
- [x] File Analysis
  - [x] Metadata extraction (MIME, hashes MD5/SHA-256, file stats, Hachoir internals)
  - [x] ASCII string extraction (min length configurable)
  - [x] VirusTotal file scan (hash lookup + upload up to 650 MB)
  - [x] Tail data detection (hidden data after PNG IEND marker)
  - [x] Drag-and-drop file selection
- [x] Metadata Cleaning (EXIF / metadata stripper)
  - [x] JPEG (EXIF stripping via piexif / Pillow)
  - [x] PNG, GIF, BMP, TIFF (re-encode via Pillow)
  - [x] PDF (rewrite without doc info via PyPDF2)
  - [x] DOCX, XLSX, PPTX (clear core properties)
  - [x] ODT, ODS (remove `<office:meta>` via odfpy)
  - [x] EPUB (strip OPF metadata)
  - [x] RTF (remove `\info` block)
  - [x] MP3 (ID3 tags via mutagen), FLAC (tags via mutagen)
  - [x] ZIP (recursive unzip → clean → re-zip)
- [x] MAC Address / BSSID Location
  - [x] 5 geolocation providers: Yandex, Apple, Google, Microsoft, Mylnikov
  - [x] Interactive Leaflet.js map via QWebEngineView
  - [x] Multi-MAC lookup support
- [x] Search for email information (which resources were registered on)
  - [x] intelx.io (search, bucket content, record details)
- [x] Username search
  - [x] Sherlock-style local search (~3307 sites, regex validation, WAF detection)
  - [x] Maigret search (~510 sites, chunked async, rich reporting)
- [x] GitHub OSINT
  - [x] User / repository search
  - [x] Email search in commits
  - [x] Secret scanning (270+ patterns across 17 categories: generic, SSH, AWS, Azure, GCP, DB URLs, Stripe, GitHub/GitLab tokens, Slack, AI services, communication APIs, Docker/K8s, CI/CD, message brokers, cloud storage, JWT/OAuth)
  - [x] Multi-token support (semicolon-separated, auto-rotation on rate-limit)
  - [x] Code dorking (code, commits, issues, repos, users)
- [x] Phone number OSINT
  - [x] Parse & Validate (phonenumbers): country, region, carrier, line type, timezone
  - [x] Reverse Lookup (NumVerify / AbstractAPI APIs)
  - [x] Leak check via IntelX
- [x] Blockchain Transaction Search
  - [x] 10 supported networks: TRON, TON, ETH, BSC, BASE, SOL, BTC, LTC, DOGE, BCH
  - [x] Search by date, time (UTC), amount, and memo — without TX hash
  - [x] Confidence scoring (time proximity, amount match, memo match)
  - [x] Optional API keys for higher rate limits (TronGrid, Etherscan, BscScan, TON, Helius)
  - [x] Powered by TXFetch engine (thirdparty/txfetch)
- [x] Interactive Graph Editor
  - [x] Draggable nodes with title and content
  - [x] 4 connection ports per node (left, right, top, bottom)
  - [x] Directed edges with cubic bezier curves and arrowheads
  - [x] Drag-to-connect from any port
  - [x] Context menu: add, edit, delete nodes and edges
  - [x] Rubber band selection, Delete key removal
  - [x] Mouse wheel zoom
  - [x] JSON save/load via file dialog (default ~/.skyfall/data/)
  - [x] Theme-aware colors from QSS (dark/light)
  - [x] Node selection highlighting (accent border)
- [ ] Reverse Image Search With Yandex and Google

## `SETUP SEARXNG`

To work with dorking, you need to run searxng via docker:

```bash

docker compose up --build

```

## `DOWNLOAD`

```bash

git clone https://github.com/Nighty3098/SkyFall --recurse-submodules

```

## `RUN`

```bash

python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt

python3 main.py

```

## `CONTACTS`

Main Developer: https://t.me/Night3098

GitHub: https://github.com/Nighty3098
