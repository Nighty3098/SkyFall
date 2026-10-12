# SkyFall — Feature Documentation

**SkyFall 1.0.1** — a desktop OSINT toolkit for digital investigations.
Built with **Python 3** + **PySide6 (Qt 6)**; the interface is loaded from `resources/form.ui`.
Author: Nighty3098.

---

## Table of Contents

1. [Architecture](#architecture)
2. [Installation and Launch](#installation-and-launch)
3. [Settings and API Keys](#settings-and-api-keys)
4. [Cases (Case Manager)](#cases-case-manager)
5. [Program Tabs](#program-tabs)
   - [Telegram Downloader](#telegram-downloader)
   - [Telegram Analyzer](#telegram-analyzer)
   - [Username](#username)
   - [Mail](#mail)
   - [Social](#social)
   - [Reddit](#reddit)
   - [Leaks](#leaks)
   - [Geo](#geo)
   - [Archive](#archive)
   - [Dorking](#dorking)
   - [Web](#web)
   - [File Analyze](#file-analyze)
   - [GitHub](#github)
   - [Phone](#phone)
   - [MAC Addr](#mac-addr)
   - [Blockchain](#blockchain)
   - [Steganography](#steganography)
   - [Search4Faces](#search4faces)
   - [Graph](#graph)
   - [AI Report](#ai-report)
   - [Settings](#settings)
   - [Proxy](#proxy)
6. [Graph](#graph-1)
7. [MCP Servers](#mcp-servers)
8. [Code Structure](#code-structure)
9. [Data and Storage](#data-and-storage)

---

## Architecture

```
main.py → src/connectors.py (Qt signals) → src/controllers/ → src/modules/ (data collection)
                                                └── src/libs/ (graph)
                                                └── src/mcp_controller.py, graph_bridge.py
```

- **Controllers** (`src/controllers/`) — UI logic: read/write widgets, call modules.
- **Modules** (`src/modules/`) — UI-independent data collection via external APIs.
- **Connectors** (`src/connectors.py`) — bind Qt widget signals to controller methods.
- **qasync loop** — all long-running operations are started via `asyncio.ensure_future` / `run_in_executor` / `asyncio.to_thread`.
- **Output formatting** — shared helpers in `src/ui/output_formatter.py`: `divider`, `title`, `section`, `kv`, `bullet`, `line`, `info`, `error`, `end_of`.
- **Hotkeys** (`src/shortcuts.py`): `Ctrl+Tab` / `Ctrl+Shift+Tab` — switch tabs, `Ctrl+Shift+b` — show/hide navigation.

---

## Installation and Launch

```bash
# Clone with submodules (required for txfetch)
git clone https://github.com/Nighty3098/SkyFall --recurse-submodules

# Virtual environment
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt

# Dorking: start a local SearXNG (optional, for SearXNG mode)
docker compose up --build

# Launch
python3 main.py
# Debug mode
python3 main.py -d
```

**Development:** `./check.sh` (lint), `./format.sh` (autoformat).

**Telegram:** for the downloader to work, you must first authorize a session via `setup_telegram.py` (creates `tg_session.session`).

---

## Settings and API Keys

All settings are stored in `~/.skyfall/settings.json`. They are saved with the **Save** button on the **Settings** tab; after saving, the keys are automatically picked up by the running modules.

| Key | Widget | Purpose |
|---|---|---|
| `path_to_storage` | `pathToStorageEdit` | Data storage directory |
| `tg_api_key` | `tgApiKeyEdit` | Telegram API ID |
| `telegram_api_hash` | `telegramApiHashEdit` | Telegram API Hash |
| `telegram_phone` | `telegramPhoneEdit` | Telegram account phone number |
| `intelligent_x_api_key` | `intelligentXApiKeyEdit` | IntelX (email, phone, leaks) |
| `hibp_api_key` | `hibpApiKeyEdit` | Have I Been Pwned |
| `virustotal_api_key` | `virustotalApiKeyEdit` | VirusTotal (domains, files) |
| `google_safe_api_key` | `googleSafeApiKeyEdit` | Google Safe Browsing |
| `ipinfo_api_key` | `ipinfoApiKeyEdit` | ipinfo.io IP geolocation |
| `github_token` | `githubTokenEdit` | GitHub PAT (multiple separated by `;` for rotation) |
| `numverify_api_key` | `numverifyApiKeyEdit` | NumVerify (phones) |
| `abstractapi_api_key` | `abstractapiApiKeyEdit` | AbstractAPI (phones) |
| `trongrid_api_key` | `trongridApiKeyEdit` | TronGrid (blockchain) |
| `abuseipdb_api_key` | `abuseipdbApiKeyEdit` | AbuseIPDB (IP reputation, threat intel) |
| `greynoise_api_key` | `greynoiseApiKeyEdit` | GreyNoise (optional, raises community API limits) |
| `etherscan_api_key` | `etherscanApiKeyEdit` | Etherscan (Ethereum + Base) |
| `bscscan_api_key` | `bscscanApiKeyEdit` | BscScan (BSC) |
| `tonapi_api_key` | `tonapiApiKeyEdit` | TonAPI (TON) |
| `helius_api_key` | `heliusApiKeyEdit` | Helius (Solana) |
| `leakcheck_api_key` | `leakcheckApiKeyEdit` | LeakCheck API v2 (optional; without a key — public endpoint) |
| `dehashed_email` | `dehashedEmailEdit` | Dehashed — account email (basic auth) |
| `dehashed_api_key` | `dehashedApiKeyEdit` | Dehashed API key |
| `firms_map_key` | `firmsMapKeyEdit` | NASA FIRMS MAP_KEY (active fires) |
| `reddit_client_id` | `redditClientIdEdit` | Reddit OAuth Client ID (optional; live profile) |
| `reddit_client_secret` | `redditClientSecretEdit` | Reddit OAuth Client Secret (optional; live profile) |
| `light_theme` | `lightThemeCheck` | Light theme (palette in `src/ui/theme.py`) |
| `frameless_window` | `framelessCheck` | Frameless window |
| `mcp_require_auth` | `mcpAuthCheck` | Require a bearer token for the MCP server |

> **Security.** All key values from the table (`*_api_key`, `*_token`, `telegram_api_hash`, `telegram_phone`) are **encrypted** (Fernet, `enc:v1:`) before being written to `settings.json`. The key is stored in `~/.skyfall/secret.key` with `0600` permissions; `settings.json` itself and the `~/.skyfall` directory — `0600`/`0700`. Legacy plaintext files are read as-is and re-encrypted on the next **Save** (`src/security.py`).

Additionally, the Settings tab has an **MCP Server** block (`mcpStatusLabel`, `mcpToggleButton`) to start/stop the built-in MCP server.

---

## Cases (Case Manager)

`src/case_manager.py` — the concept of an investigation "case". Menu **SkyFall → New case / Open case**.

- When a case is created/opened, a folder structure is generated: `domains`, `telegram`, `username`, `email`, `social`, `reddit`, `leaks`, `geo`, `archive`, `github`, `phone`, `mac`, `blockchain`, `files`, `steganography`, `reports`, `dorking`, `downloads` + `graph`.
- **Autosave**: the contents of all debug panels are automatically saved to timestamped Markdown files (`YYYY-MM-DD_HH-MM-SS_<label>.md`) in the corresponding categories. Recurring (extended) content overwrites the current file instead of creating a new one.
- The case name is shown in the SkyFall menu.
- Directories: `<case>/graph`, `<case>/reports` (if there is no case — `~/.skyfall/data`).

---

## Program Tabs

All 24 tabs are opened via the side menu (navigation), grouped into sections: **Home**, **Telegram**, **Identity & OSINT**, **Web & Infrastructure**, **Workspace**, **System**. The menu is toggled via **View → Toggle Navigation** (or `Ctrl+Shift+B`). The UI theme (dark/light) is generated from a single template `resources/style.template.qss` + the palette in `src/ui/theme.py` — both themes use the same set of rules and do not "drift apart".

Additionally (`src/ui/layout_polish.py`):
- **Scrolling in settings.** The long column of fields on the **Settings** tab is wrapped in a `QScrollArea`, so the minimum window size is no longer dictated by its height.
- **Responsive width.** The toolbar of the **Graph** tab can shrink (button text is truncated only in a very narrow window), which reduced the minimum window width from ~1463 to ~934 px.
- **Accessibility.** The contrast of muted text was raised to ≥4.5:1, visible focus states were added for fields/lists/checkboxes, checkboxes are visually distinct from radio buttons (square vs circle), and the progress-bar fill uses a tone on which the completion percentage stays readable.

### Telegram Downloader

Collecting data from a Telegram channel/group via MTProto (the Telethon library) into the SQLite `SkyFall_TG.db`.

**Fields and elements:**
- `telegramUsernameEdit` — channel username (e.g. `@channel` or `channel`).
- `telegramUseProxyCheck` — use a proxy from the list (`~/.skyfall/proxies.txt`).
- **Safety Delays**: `telegramBaseDelay` (pause between requests), `telegramMaxReq` (request limit), `telegrammembersDelay` (pause when collecting members), `telegramPause` (pause duration).
- `telegramDownloadMediaCheck` — download media files.
- `telegramCollectMembersCheck` — collect channel members.
- `telegramCollectLinksCheck` — collect links from messages.
- `telegramMultiAccCheck` — multi-account (rotation of `.session` files).
- `telegramDownloadStart` — start collection.
- `telegramDownloadProgress` — progress (stages: channel / discussion / avatars / done).
- `telegramDownloadAvatarsBtn` — separately finish downloading member avatars.
- `telegramAccountInfo` — information about the account used.
- `telegramDownloaderDebug` — process log.

**What is collected:**
- Channel/group, members, messages (text, media, views, reposts, author), forwards, discussions (linked chat), links from text, user profiles (including business fields and birthday via `GetFullUserRequest`).
- Media into the `SkyFall_TG_media/<channel>/` folder (posts and `discussion_<id>/`), avatars into `avatars/<user_id>.jpg`.

**Capabilities:**
- Resuming from where it stopped (by the last `post_id`).
- Proxy rotation (MTProto `host:port:secret`, `t.me/proxy` links, SOCKS4/SOCKS5/HTTP) on errors/flood.
- Automatic switching to another account when the request limit is exhausted.
- Handling `FloodWaitError` and "smart" pauses.

### Telegram Analyzer

Analyzing the downloaded `SkyFall_TG.db` database and building a relationship graph.

**Fields and elements:**
- `telegramAnalyzerLoadChannelsButton` — load the channel list (path from `pathToStorageEdit` or `~/.skyfall/data`).
- `telegramChannelsList` — channel selection (or "All Channels").
- `includeLinksCheck` — include link-based connections (nodes `domain:*`).
- `telegramAnalyzerStartDate` / `telegramAnalyzerEndDate` — post date filter.
- `telegramAnalyzerMinReplies` — minimum number of replies for a user↔user connection.
- `includeForwardingCheck` — include forward-based connections.
- **Export**: `telegramAnalyzerGraphMLCheck`, `checkBox_7` (GEXF), `telegramAnalyzerJSONCheck`, `telegramAnalyzerCSVCheck`, `checkBox_8` (CSV edges), `telegramAnalyzerPNGCheck`, `telegramAnalyzerHTMLCheck` (interactive pyvis), `telegramAnalyzerObsidianCheck` (Obsidian vault).
- `runTelegramAnalyzerBtn` — start the analysis.
- `telegramAnalyzerProgress`, `telegramAnalyzerDebug`.

**The graph includes:**
- User, channel, and domain nodes.
- Edges: membership (`member`), replies (`replier`, weighted), forwards (`forwarded`), discussion replies (`discussion_reply`), mentions (`mentions`), shared members between channels (`shared_members`, optional).
- Statistics: number of nodes/edges, degrees, bots/verified/premium.

**Export formats:** GraphML, GEXF, JSON (node-link), CSV (nodes/edges), PNG (matplotlib), HTML (pyvis with a node-info panel), Obsidian Markdown (channel/member files with wiki-links and embedded avatars).

The **To Main Graph** button (`tgToGraphButton`) rebuilds the TG graph from the database with the current filters and loads it into the main graph (`src/modules/graph_io.py`: user→Person, channel→Organization, domain→Domain; member→member_of, replier/discussion_reply→communicates_with, forwarded/mentions/linked_chat→linked_to, shared_members→associated_with; spring layout). It also supports importing TG export files and exporting the canvas to PNG/SVG.

### Username

Searching a username across hundreds of sites with two engines.

- `usernameEdit` + `searchUsernameButton` — start.
- `usernameSearchProgress` — overall progress.
- `usernameResultsDebug` — a **single** report from both engines: **Maigret** (an engine over ~510 sites, chunked search) and **Sherlock-like** search (built-in database `data/username_data.json`, ~481 sites; if no local database is present — the remote `https://data.sherlockproject.xyz`).
- A link found by **both** engines is considered confirmed and is displayed **at the top** with a ✅ mark; one found by only one engine goes to the bottom, grouped by source engine (`src/modules/username_merge.py`). A match is determined by the normalized profile URL, and if they don't match — by the site name.

Each site is checked for username availability (statuses: CLAIMED / AVAILABLE / UNKNOWN / ILLEGAL / WAF), taking into account WAF signatures (Cloudflare, AWS WAF, PerimeterX).

### Mail

Search by email address.

- `mailEdit` — email.
- `startMailSearchButton` — **IntelX** search: create a search task → poll results → download bucket contents. Output to `mailSearchDebug`: list of databases (Found N databases), bucket ID, date, size, source, tags, contents.
- `startHibpCheckButton` — **Have I Been Pwned**: list of breaches (name, domain, date, number of compromised accounts, data classes). Output to `hibpDebug`. `Retry-After` is honored on 429.
- `analyzeEmlButton` — **EML / Headers**: select an `.eml` file (or paste raw headers into `mailEdit`) → parse into `emailHeaderDebug`: envelope (From/Reply-To/Return-Path/Message-ID), Received chain (per hop with IP), SPF/DKIM/DMARC from `Authentication-Results`, DNS check of the sender domain's SPF/DMARC records, origin IP geo (rDNS + ip-api.com: country/city/ISP/ASN, proxy/hosting flags), verdict LOW/MEDIUM/HIGH.
- `emailAccountsButton` — **Registered Accounts** ("where the email is registered"): parallel service checks → `emailAccountsDebug`. Built-in keyless checks: **Gravatar, Microsoft, Mozilla, ProtonMail, Duolingo, Twitter/X**. In addition, a full run of the **`holehe`** package is performed (~120 sites, included in `requirements.txt`); the output is grouped into "Registered / Not found / Unknown".

### Social

Searching a username on open social networks that have public APIs: **Bluesky** (AT Protocol), **Mastodon** (ActivityPub) and **Instagram** (`instaloader`).

- `socialUsernameEdit` — username/handle; `socialInstanceEdit` — Mastodon instance (default `mastodon.social`).
- `socialSearchButton` — **Search All**: profile + matches on both networks. `socialBlueskyButton` / `socialMastodonButton` / `socialInstagramButton` — search only one.
- **Bluesky**: `app.bsky.actor.getProfile` (exact profile, handle `name` or `name.bsky.social`) + `app.bsky.actor.searchActors` (similar accounts).
- **Mastodon**: `/api/v1/accounts/lookup` (exact account on the instance) + `/api/v2/search?type=accounts` (matches).
- **Instagram**: public profile via **`instaloader`** (no login; Instagram often limits anonymous requests — the error is output gently): name, followers/following, posts, privacy, verification, external link.
- Output — to `socialDebug`: handle, display name, followers/following/posts, creation date, bio.

### Reddit

OSINT profile of a Reddit account by username via the public archives **Arctic Shift** (`arctic-shift.photon-reddit.com`) and **PullPush** (`api.pullpush.io`). No keys are needed. Unlike the reference source, pagination of both archives (posts and comments) runs **in parallel** (`asyncio.gather`), the results are merged by `id`, and each item is classified as **live**, **removed** (moderator action) or **deleted** (author action).

- `redditUsernameEdit` — username (with or without `u/`); `redditSourceCombo` — both archives / Arctic Shift only / PullPush only.
- `redditSubredditEdit` — subreddit filter; `redditKeywordsEdit` — keywords (full-text search and the **Archive Search** button).
- `redditNsfwCombo` — NSFW filter (Any / Safe only / NSFW only); `redditMaxPagesSpin` — page limit per source.
- Buttons: **Full Report**, **Posts**, **Comments**, **Removed / Deleted**, **Identifiers**, **Activity & Timezone**, **Subreddits & Tech**, **Archive Search**.
- Report: post/comment counts, statuses, activity over 12 months, **PII exposure score (0–100)**, histograms by hour (UTC)/day/month, **timezone estimate** from "quiet" hours, top subreddits, identifiers (email, BTC/ETH/XMR, Telegram, phones, domains, mentions) and mentioned technologies.
- **Live profile** (optional): when `reddit_client_id` / `reddit_client_secret` are set, the module obtains an app-only OAuth token and requests `/user/{name}/about` — current karma, creation date, ban flag. Without keys, only archival statistics are used.
- Archive throttling (HTTP 429/5xx) is handled with retries and exponential backoff; when proxies are configured, the shared proxy list is used.
- Output — to `redditOsintDebug`; results are autosaved to the case's `reddit` category.
- Code: `src/modules/reddit_osint.py`, `src/controllers/reddit_osint_controller.py`, the `redditOsintTab` tab in `resources/form.ui`; tests — `tests/test_reddit_osint.py`.

### Leaks

Searching for leaks and infostealer logs by email, username, or domain.

- `leakTargetEdit` — target (email / username / domain; the type is detected automatically).
- `leakSearchAllButton` — **Search All**: aggregates all available sources.
- `leakInfostealerButton` — **Infostealer (Hudson Rock)**: free Cavalier API without a key — infected machines, compromise date, OS, top logins/passwords, IP.
- `leakLeakCheckButton` — **LeakCheck**: without a key — the public endpoint (record count, sources, fields); with `leakcheck_api_key` — API v2.
- `leakHibpButton` — **Have I Been Pwned** (requires `hibp_api_key`).
- `leakDehashedButton` — **Dehashed** (requires `dehashed_email` + `dehashed_api_key`).
- Output — to `leakDebug`; errors/missing keys are reported informationally.

### Geo

Geo analysis: sun/shadow calculations (locally, `suncalc`), NASA FIRMS fires, and GDACS disasters.

- `geoCoordEdit` — coordinates `lat, lon`; `geoDateTimeEdit` — date/time (UTC) for the sun calculation.
- `geoSunShadowButton` — **Sun / Shadow**: sun azimuth/altitude, shadow azimuth, and shadow length ratio.
- `geoShadowRatioEdit` / `geoShadowBearingEdit` — shadow ratio (length/height) and shadow azimuth; `geoShadowSearchButton` — **Shadow Geolocation**: reverse lookup of coordinates (globe grid, 2° step) whose sun position matches the observation (analogous to ShadowFinder).
- `geoFirmsButton` — **FIRMS Fires**: active fires in a ±2° area (requires `firms_map_key`).
- `geoGdacsButton` — **GDACS Disasters**: alerts for the last 30 days (no key).
- `geoFullReportButton` — **Full Report**: sun/shadow + nearby fires.
- Output — to `geoDebug`.

> **Note.** `shadowfinder`/`timezonefinder`/`cartopy` are intentionally **not** used: they pull in `cffi<2`, which conflicts with `cryptography`. The lightweight `suncalc` is used for shadow calculations.

### Archive

Working with web archives and evidence capture.

- `archiveUrlEdit` — URL (the scheme is added automatically).
- `archiveCheckButton` — **Check Archives**: nearest Wayback snapshot + presence in archive.today.
- `archiveAvailabilityButton` — **Wayback Closest**: a quick availability API request (tries the URL with and without the scheme).
- `archiveSnapshotsButton` — **Wayback Snapshots**: snapshot list via CDX (slow on some networks, errors are soft).
- `archiveSaveButton` — **Save to Wayback**: submit the URL for archiving (via `waybackpy`, may take time).
- `archiveTodayButton` — **archive.today**: check for a snapshot (`archive.ph`).
- Output — to `archiveDebug`.

### Dorking

Google dorks from the `data/dorks.json` database (14 categories, ~7,944 dorks; `dorks.xml` also exists).

- `dorksCategoryList` — category (double-click loads dorks), `dorksCategorySearchEdit` — filter.
- `dorksList` — dork list (double-click starts a search), `dorksListSearchEdit` — filter, context menu "Move to edit".
- `customDorkEdit` + `dorkItButton` — run an arbitrary dork.
- `useSearxngCheck` — use a local **SearXNG** (`http://localhost:8080`), otherwise **DuckDuckGo** (the `ddgs` library).
- `useCustomDorkCheck` — use the custom dork from the input field.
- `dorksResult` — results, `dorksResultSearchEdit` — highlight the found text in the results.

### Web

Full domain analysis — 16 steps (selected by checkboxes, progress `domainProgress`).

| Checkbox | Panel | What it does |
|---|---|---|
| `domainRobotsCheck` | `serverRobotsDebug` | robots.txt |
| `domainLocationCheck` | `serverLocationDebug` | IP + geolocation (ipapi.co, ip-api.com, ipinfo.io) |
| `domainSSLCheck` | `serverTlsDebug` | SSL/TLS certificate (version, cipher, issuer, validity) |
| `domainDNSCheck` | `serverDnsAnalyzeDebug` | DNS: A/MX/TXT/NS/CNAME/SOA + NS IP addresses + standard hosts |
| `domainHeadersCheck` | `serverWafDebug` | HTTP headers, web server, WAF, technology stack |
| `domainWhoisCheck` | `serverWhoisDebug` | WHOIS |
| `domainNmapCheck` | `serverNmapDebug` | NMAP port scan 1-1024 (`--script=vuln`, requires system nmap) |
| `domainMalwareCheck` | `serverMalwareDebug` | Reputation (aggregator): VirusTotal + Google Safe Browsing + CRDF Labs + AbuseIPDB + GreyNoise + ThreatFox + URLHaus, overall verdict |
| `domainSubdomainsCheck` | `serverSubdomainsDebug` | Subdomains: DuckDuckGo + crt.sh + AlienVault OTX + HackerTarget + AnubisDB + DNS brute-force over a built-in top list |
| `domainJsSecretsCheck` | `serverJsSecretsDebug` | JS Secrets: collect `<script src>`, scan up to 15 JS files for API keys/secrets/endpoints (23 regexes + keywords from GitHub search), secrets are redacted |
| `domainThreatIntelCheck` | `serverThreatIntelDebug` | One-click Threat Intel: AbuseIPDB + GreyNoise + ThreatFox + URLHaus with automatic domain-to-IP resolution |
| `securityTxtCheck` | `securityTxtDebug` | `/.well-known/security.txt` |
| `cookiesCheck` | `cookiesDebug` | Site cookies |
| `socialTagsCheck` | `socialTagsDebug` | OpenGraph / Twitter meta tags |
| `certTrCheck` | `certTrDebug` | Certificate Transparency via crt.sh |
| `domainsOnIpCheck` | `domainsOnIpDebug` | Reverse lookup: domains on an IP (PTR, Shodan InternetDB, HackerTarget) |

Additionally: `serverUrlEdit` + `runUrlScanButton` — specify a domain and run the analysis.

### File Analyze

File analysis (by dragging into `metadataFileDropWidget` or with the `getMetadataButton` button).

- `fileMetadataCheck` → `metadataDebug`: metadata (size, MIME, MD5/SHA-256 hashes, timestamps, permissions, Hachoir dump) + a check for "trailing" data after the end of the file (`check_tail_data`). If GPS coordinates are present — a Leaflet map in `metadataMapView` (OpenStreetMap, marker at the coordinates).
- `fileStringsCheck` → `stringsFileDebug`: printable ASCII strings (min_len=4).
- `fileVirustotalCheck` → `virustotalFileDebug`: VirusTotal — check by SHA-256; if the file is not found — upload for scanning (up to 650 MB, large files via a large upload URL) and wait for the result.
- `cleanMetadataButton` — strip metadata from the file in place (see the `metadata_cleaner` module), then re-analyze.

**Metadata stripping supports:** ZIP (all entries recursively), JPEG/PNG/GIF/BMP/TIFF, PDF, DOCX, PPTX, ODT/ODS, EPUB, RTF, MP3, FLAC, XLSX.

### GitHub

Searching via the GitHub REST API. Field `githubTokenEdit` (PAT; multiple tokens separated by `;` — automatic rotation on rate limits).

- `githubUserEdit` + `githubUserSearchBtn` — user profile + their repositories (top-15 by update).
- `githubRepoEdit` + `githubRepoSearchBtn` — repository search (language, stars, forks, description).
- `githubCommitEdit` + `githubCommitSearchBtn` — commit search (by username/repo or any query).
- `githubEmailEdit` + `githubEmailSearchBtn` — email search in code (`<query> email OR @ OR .com`).
- `githubSecretEdit` + `githubSecretSearchBtn` — secret search: iterates ~240 secret patterns (API keys, SSH, AWS/Azure/GCP, DB strings, Stripe, GitHub/GitLab tokens, Slack, OpenAI, Twilio, Docker/K8s, JWT/OAuth, etc.). Pattern progress in `githubProgress`.
- `githubDorkEdit` + `githubDorkSearchBtn` + `githubDorkGroup` — an arbitrary GitHub dork by type: code / commits / issues / repositories / users.
- Results — in `githubDebug` with progress and remaining limits (`[Page N] Rate: r/lim`).

### Phone

Phone number analysis.

- `phoneNumberEdit` — number; `phoneRegionEdit` — default region (e.g. `RU`).
- `phoneParseBtn` → `parse_validate`: parsing/validation (phonenumbers): formats, country code, region, type, carrier, geolocation, time zones.
- `phoneLookupBtn` → `reverse_lookup`: reverse lookup via **NumVerify** and **AbstractAPI** (keys required).
- `phoneLeakBtn` → `check_leaks`: leaks via **IntelX** (search → wait → results + bucket contents).
- `phone7telBtn` → `search_7tel`: reviews/rating on **7tel.ru** (no keys; scraping: score, number of negative reviews, review list, similar numbers).
- `phoneProgress`, `phoneDebug` — progress and output.

### MAC Addr

MAC address (BSSID) geolocation via five providers: **Yandex, Apple, Google, Microsoft, Mylnikov** (unofficial protocols: XML/Protobuf).

- `macAddrEdit` + `checkMacAddrButton` — start.
- `macAddrLocationDebug` — coordinates per provider.
- `macLocationMapView` — a Leaflet map with all found coordinates.

### Blockchain

Searching for transactions by indirect data (amount, time, network, memo) via the bundled **txfetch** library (thirdparty).

- `bcNetworkCombo` — network: Tron, TON, Ethereum, BSC, Base, Solana, Bitcoin, Litecoin, Dogecoin, Bitcoin Cash.
- `bcCoinCombo` — coin.
- `bcDateEdit` — date or range (`DD.MM.YYYY` / `DD.MM.YYYY-DD.MM.YYYY`).
- `bcTimeEdit` — time (`HH:MM[:SS]`).
- `bcTimeRangeCombo` — precision: exact / ±1 min / ±5 min / ±15 min / custom.
- `bcAmountEdit` — amount or range `min-max`.
- `bcToleranceSpin` — amount tolerance (fractions).
- `bcMemoEdit` — memo (for TON).
- `bcSearchButton` + `bcProgressBar` — start; results in `bcDebug`: tx_id, confidence %, time, amount/coin, score breakdown Δt/ΔA/ΔT/M, from/to addresses, memo.

**Keys:** TronGrid, Etherscan (ETH+Base), BscScan, TonAPI, Helius (Solana). BTC/LTC/DOGE/BCH — public nodes without keys.

### Steganography

Analyzing images for hidden data (drag into `steganoFileDrop`).

- `LSBDebug` — **LSB analysis**: bit counters per R/G/B/A channel, ratios, chi-square test, alpha-channel uniqueness check, capacity estimate.
- `spectralAnalysisDebug` — **spectral analysis** (FFT): low/high frequency energy, ratios, variance of mid frequencies and diagonals, anomalies.
- `EOIDebug` — **end of file** (EOI/EOD): search for a "tail" after PNG/JPEG/GIF/BMP/TIFF/WebP markers, hex dump, and content identification (ZIP, GZIP, RAR, ELF, PE, PDF, SQLite, HTML, URL, etc.).
- `tailDataDetectionDebug` — general detection of hidden data at the end of the file.
- `elaDebug` — **ELA (Error Level Analysis)**: recompress to JPEG Q=90, difference from the original, statistics (mean/std/p95, hot-pixel share, hot 8x8 blocks), the heatmap is saved alongside as `<name>_ela.png`, verdict (uniform / localized edit / resaved).

### Search4Faces

Reverse face search via the **search4faces.com** service (VK photos; scraping private AJAX endpoints).

- `s4fFileDrop` — drag a face photo (displayed in `s4fTargetLabel`).
- `runS4FButton` — start the search.
- Results — `S4FResultWidget` cards in `s4fResultsScrollArea`: face thumbnail, first/last name, age, city, country, similarity %, VK link.
- `s4fSearchEdit` — search among the profiles in the results (Enter — jump to the next match).

### Graph

A visual relationship graph with an entity palette (`entityPalette`, drag onto the canvas) and a node editing panel.

- `entitySearchEdit` — palette filter.
- `graphWidget` — canvas (see [Graph](#graph-1)).
- `exportGraphButton` / `importGraphButton` — save/load a JSON graph; import also understands TG Analyzer exports (GraphML/GEXF/node-link JSON/CSV pair) with entity mapping and auto-layout.
- `exportGraphImageButton` — export the canvas to PNG (x2) / SVG.
- `graphClearButton` — clear the graph.
- `graphLayoutCombo` + `graphAutoLayoutButton` — automatic layout (spring / kamada_kawai / shell / spectral / circular).
- `graphSearchEdit` + `graphClearFilterButton` + `graphFilterCombo` — filtering by text and entity type.
- Node panel: `nodeTitleEdit`, `nodeTypeCombo`, `nodeContentEdit`, `nodeEvidenceList`, `nodeEvidenceAddFileBtn`, `nodeEvidenceAddUrlBtn`, `nodeEvidenceRemoveBtn`.

### AI Report

Generating a final OSINT report via a local **Ollama** (MCP server `ollama_mcp_server.py`).

- `updateOllamaListButton` + `ollamaModelsSelector` — list of models from Ollama (`http://127.0.0.1:11434`).
- `aiReportLangEdit` — report language (default `Russian`).
- `generateReportButton` — collect all results (~28 debug panels + graph data + search inputs) and generate a structured report (7 sections, confidence markers `[FACT]/[INFERRED]/[HYPOTHESIS]`).
- `saveReportButton` — save the report to Markdown (`<case>/reports/`).

### Settings

See [Settings and API Keys](#settings-and-api-keys). Also the **MCP Server** block: `mcpStatusLabel` + `mcpToggleButton` — start/stop the built-in MCP server (SSE on `127.0.0.1:9877`).

### Proxy

- `proxyListEdit` — proxy list (one per line); `saveProxiesButton` — save to `~/.skyfall/proxies.txt`.
- Formats: `t.me/proxy?...`, `tg://proxy?...`, `type://host:port`, MTProto `host:port:secret` / `secret@host:port`, `user:password@host:port` (SOCKS4/SOCKS5/HTTP).

---

## Graph

### Entities (13 types)

| Type | Color | Symbol |
|---|---|---|
| Person | `#4ecdc4` | 👤 |
| Domain | `#45b7d1` | 🌐 |
| IP | `#f9ca24` | 📡 |
| Email | `#6c5ce7` | ✉️ |
| Phone | `#fd79a8` | 📱 |
| MAC | `#d35400` | 🔌 |
| Username | `#00b894` | @ |
| Crypto | `#f39c12` | ₿ |
| Organization | `#e17055` | 🏢 |
| Passport | `#e84393` | 📄 |
| Photo | `#a29bfe` | 🖼️ |
| Geolocation | `#55efc4` | 📍 |
| Custom | `#636e72` | ⚙️ |

### Relations (12 types)

`owns`, `registered_at`, `resolved_to`, `member_of`, `located_at`, `communicates_with`, `associated_with`, `works_at`, `created_by`, `attends`, `hosted_by`, `linked_to`.

Edge styles: `normal` (solid), `dashed` (dotted), `bold` (thickened). Edges are cubic Bézier curves with an arrow, a relation-type chip, and an optional label.

### Canvas Capabilities

- Nodes: move, resize (corner handle), drag ports to create edges, double-click — edit dialog.
- **Photo nodes** — a gallery of thumbnails from files/URLs (with caching and a `+N` badge).
- **Geolocation nodes** — a built-in map (OpenStreetMap tiles, zoom 5–18, marker, Ctrl+wheel to zoom).
- Context menu: edit node/edge, edge style, attach evidence, color, delete; **Analysis** — shortest path (by click), degree centrality (node scaling + top-5), community detection (greedy modularity).
- **⚡ Transforms** (graph enrichment, `graph_transform_controller`): child result nodes are built from a node and arranged in an arc:
  - **Username** → social search, Maigret, Sherlock + Maigret (merged — links confirmed by both engines), Bluesky/Mastodon, Reddit OSINT (archival profile: top subreddits, identifiers, external domains, mentioned users, technologies), Infostealer/Leaks;
  - **Domain** → IP, DNS, SSL/TLS, web stack, WHOIS, subdomains, Certificate Transparency, social tags, reputation, security.txt, cookies, robots.txt, ports, JS Secrets, Threat Intel, Infostealer/Leaks, Wayback Snapshots;
  - **IP** → geolocation, ports, domains on IP, Threat Intel;
  - **Email** → IntelX, Registered Accounts, Infostealer/Leaks;
  - **Phone** → parsing, reverse lookup, leaks;
  - **MAC** → geolocation;
  - **Geolocation** → Sun/Shadow, Nearby Disasters (GDACS).
- Persistence: JSON (`to_dict`/`from_dict`, `save_to_json`/`load_from_json`).

---

## MCP Servers

### SkyFall MCP Server (`src/skyfall_mcp_server.py`) — 89 tools

FastMCP server: `--host 127.0.0.1 --port 9877`, transports `stdio`/`sse`. Started/stopped from the Settings tab (MCP button) or via `McpController`.

**Authorization (optional).** If `mcpAuthCheck` ("Require MCP Auth") is enabled, the server requires the header `Authorization: Bearer <token>`, otherwise it responds `401`. The token is stored in `~/.skyfall/mcp_token` (`0600` permissions, generated automatically). The state can also be overridden with the environment variables `SKYFALL_MCP_REQUIRE_AUTH=1` and `SKYFALL_MCP_TOKEN=<token>` when running standalone.

**Ollama (4):** list models, set/get model, set URL.

**Domains (16):** ip, domains on IP, DNS, WHOIS, SSL, headers, web stack, nmap, WAF, reputation aggregator, threat intel, JS secrets, subdomains (passive + brute), robots.txt, security.txt, social tags.

**Username (3):** Sherlock-like search (`skyfall_username_search`), maigret (`skyfall_maigret_search`), cross-check of both engines with match confirmation (`skyfall_username_merged`).

**Social (2):** Bluesky + Mastodon search (`skyfall_social_search`), Instagram profile (`skyfall_instagram_profile`).

**Reddit (8):** `skyfall_reddit_report` (aggregated profile from the Arctic Shift + PullPush archives), `skyfall_reddit_posts`, `skyfall_reddit_comments`, `skyfall_reddit_removed` (removed by moderators/author), `skyfall_reddit_identifiers` (email, crypto, Telegram, domains, mentions, exposure score), `skyfall_reddit_activity` (histogram by hour/day/month + timezone), `skyfall_reddit_affiliations` (top subreddits, technologies), `skyfall_reddit_archive_search` (full-text archive search). Reports are cached for 15 minutes.

**Email (6):** IntelX, HIBP, combined, `.eml` file parsing, pasted header parsing, account search by email (Gravatar/Microsoft/… + holehe).

**Leaks / infostealers (2):** `skyfall_leak_check` (Hudson Rock + LeakCheck + HIBP + Dehashed), `skyfall_infostealer_search` (Hudson Rock).

**Geo (4):** `skyfall_geo_sun_shadow` (sun/shadow), `skyfall_shadow_geolocate` (reverse coordinate lookup), `skyfall_firms_fires` (NASA fires, requires `firms_map_key`), `skyfall_gdacs_disasters` (GDACS).

**Archive (3):** `skyfall_archive_url` (Wayback + archive.today), `skyfall_archive_snapshots` (CDX), `skyfall_archive_save` (archiving).

**Phones (5):** parsing, reverse lookup, leaks, full, 7tel.

**GitHub (6):** user, repo, commits, emails, secrets, dork.

**Blockchain (1):** transaction search across 10 networks.

**MAC (1):** geolocation by providers.

**Files (5):** info, metadata, VirusTotal, tail-data, strings.

**Steganography (6):** lsb, spectral, eoi, tail, ela, full.

**Dorking (1):** search via DuckDuckGo/SearXNG.

**Graph (12, require a running GUI + graph bridge on 127.0.0.1:9878):** add/update/remove/move node, add/remove edge, get, summary, get_node, clear, file import (JSON/GraphML/GEXF/CSV), export PNG/SVG.

**Cases (2):** list cases, case contents.

**Report (1):** generate an OSINT report via Ollama.

**Faces (1):** search by photo via search4faces.

Resources: `skyfall://modules` (tool overview), `skyfall://settings` (masked keys).

### Ollama OSINT Reporter (`src/ollama_mcp_server.py`) — 6 tools

Stdio transport, Ollama `http://127.0.0.1:11434`, default model `hf.co/OBLITERATUS/Gemma-4-12B-OBLITERATED:Q8_0`.

- `set_ollama_url`, `get_ollama_model`, `set_ollama_model`, `list_ollama_models`, `generate_osint_report(data, language)` (strict 250-line system prompt: IDENTIFIER/INFRASTRUCTURE/GEOLOCATION/CONNECTION typing, confidence markers, noise filters, 7-section report structure), `skyfall_s4f_search`.

### Graph Bridge (`src/graph_bridge.py`)

TCP bridge `127.0.0.1:9878`, protocol: 4-byte length prefix (big-endian) + JSON. Actions: `add_node`, `add_edge`, `get_graph`, `get_node`, `update_node`, `move_node`, `remove_node`, `remove_edge`, `clear_graph`, `graph_summary`. All operations are marshaled to the GUI thread via a Qt signal (thread-safe). Every request must contain a `token` (the shared token from `~/.skyfall/mcp_token`); requests without a valid token are rejected (`{"error": "unauthorized"}`).

---

## Code Structure

```
main.py                     — entry point, UI loading, module/controller initialization
setup_telegram.py           — Telegram session authorization
logger_setup.py             — logger setup (loguru)
src/
  connectors.py             — binding Qt signals to controllers
  case_manager.py           — investigation cases, autosave
  security.py               — settings encryption and the shared MCP/bridge token
  report_controller.py      — AI report via Ollama
  mcp_controller.py         — MCP server lifecycle + graph bridge
  graph_bridge.py           — TCP bridge for the GUI graph for MCP
  context_menus.py          — context menus (dorks)
  shortcuts.py              — global hotkeys
  utils.py                  — list filtering, text highlighting
  searxng_search.py         — local SearXNG client
  modules/                  — data collection (UI-independent)
    js_secrets.py           — JS scan for keys/secrets/endpoints (Web)
    threat_intel.py         — AbuseIPDB/GreyNoise/ThreatFox/URLHaus aggregator
    email_accounts.py       — where the email is registered (Gravatar/Microsoft/… + holehe)
    social_search.py        — username search on Bluesky, Mastodon, Instagram
    reddit_osint.py         — Reddit archival OSINT (Arctic Shift + PullPush, OAuth live profile)
    leak_search.py          — leaks and infostealers (Hudson Rock, LeakCheck, HIBP, Dehashed)
    geo_analysis.py         — sun/shadow (suncalc), fires (NASA FIRMS), disasters (GDACS)
    archive_search.py       — web archives (Wayback Machine, archive.today)
    tg/                     — Telegram package: db, models, proxy, throttler,
                              client_manager, session_manager, users, cache, extractors, state
  controllers/              — per-tab UI logic
  libs/                     — graph_lib (graph), graph_panel (palette)
  ui/                       — setup_ui, drop_widget, output_formatter, s4f_result_widget
resources/                  — form.ui, QSS themes, fonts, icons
data/                       — dorks.json, dorks.xml, username_data.json
thirdparty/txfetch/         — vendored transaction search library
```

---

## Data and Storage

- **`~/.skyfall/`**: `settings.json` (settings/keys; sensitive values are encrypted), `secret.key` (encryption key, `0600`), `mcp_token` (bearer token for MCP/bridge, `0600`), `proxies.txt`, `logs/`, `data/` (cases, `SkyFall_TG.db`, `SkyFall_TG_media/`, graphs).
- **`data/dorks.json`** — 14 categories, ~7,944 dorks. **`data/dorks.xml`** — the original GHDB database.
- **`data/username_data.json`** — 481 site specifications for username search (URL templates, error codes, regex).
- **`resources/form.ui`** — UI (3184 lines), loaded at runtime.
- **Telegram DB** — SQLite `SkyFall_TG.db`: tables `channels`, `users`, `posts`, `discussions`, `members`, `links`.

---

## External Services (Summary)

| Service | Where used | Key required |
|---|---|---|
| Telegram MTProto | downloader/analyzer | API ID/Hash + session |
| IntelX public API | email, phone leaks, username | `intelligent_x_api_key` |
| Have I Been Pwned | email | `hibp_api_key` |
| VirusTotal API v3 | domains, files | `virustotal_api_key` |
| Google Safe Browsing | domain reputation | `google_safe_api_key` |
| ipinfo.io / ipapi.co / ip-api.com | IP geolocation | ipinfo — optional |
| GitHub REST API | search | `github_token` |
| NumVerify / AbstractAPI | phones | `numverify` / `abstractapi` |
| 7tel.ru | phones (reviews) | no |
| search4faces.com | faces | no |
| Yandex / Apple / Google / Microsoft / Mylnikov | MAC geolocation | no |
| crt.sh | Certificate Transparency | no |
| Shodan InternetDB / HackerTarget | domains on IP | no |
| AbuseIPDB | IP reputation (threat intel, malware aggregator) | `abuseipdb_api_key` |
| GreyNoise community | scanner background noise/RIOT (threat intel) | no (key is optional) |
| ThreatFox (abuse.ch) | IOC check of IP/domain | no |
| URLHaus (abuse.ch) | malicious URLs of a host | no |
| AlienVault OTX | passive DNS → subdomains | no |
| AnubisDB (jldc.me) | subdomains | no |
| CRDF Labs | domain reputation (fallback) | no |
| DuckDuckGo (ddgs) | dorks, subdomains | no |
| SearXNG (local) | dorks | no |
| Ollama | AI report | locally |
| txfetch (TronGrid/Etherscan/BscScan/TonAPI/Helius) | blockchain | yes |
| Maigret | username | no |
| Gravatar / Microsoft / Mozilla / ProtonMail / Duolingo / Twitter(X) | registered accounts (email) | no |
| holehe | registered accounts, ~120 sites | no |
| Hudson Rock Cavalier | infostealer logs (email/username/domain) | no |
| LeakCheck | leaks (public endpoint / API v2) | optional (`leakcheck_api_key`) |
| Dehashed | leaks | yes (`dehashed_email` + `dehashed_api_key`) |
| Bluesky (AT Protocol public AppView) | Social: username | no |
| Mastodon (instance ActivityPub API) | Social: username | no |
| Instagram (instaloader) | Social: username | no |
| suncalc | Geo: sun/shadow (locally) | no |
| NASA FIRMS | Geo: active fires | yes (`firms_map_key`) |
| GDACS | Geo: disasters | no |
| Wayback Machine (availability/CDX/save) | Archive | no |
| archive.today (archive.ph) | Archive | no |

**License:** MIT (see `LICENSE`, `THIRD_PARTY_NOTICES.md`).
