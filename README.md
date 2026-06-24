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
  - [x] IP info
  - [x] SSL / TLS
  - [x] DNS
  - [x] Headers
  - [x] Server Location
  - [x] Associated Hosts
  - [x] Open ports (nmap scan 1–65535)
  - [x] WHOIS (registrar, creation/expiration dates, name servers)
  - [x] Web stack (HTTP headers, web server, WAF, detected tech — Nginx, Apache, WordPress, Bitrix, jQuery)
  - [x] WAF
  - [x] Malware reputation (VirusTotal, Google Safe Browsing, CRDF Labs)
  - [x] NMAP (vuln scripts)
- [x] Dorking via duckduckgo
- [x] Telegram OSINT
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
  - [x] Link Extraction
    - [x] Automatic extraction of all URLs from messages
    - [x] Support for Telegram links (t.me, @username)
    - [x] Saving link context (surrounding text)
    - [x] Link classification by type (telegram, http, https)
  - [x] Interaction Graph Analysis
    - [x] Build interaction graphs from collected data
    - [x] Nodes: users, channels, domains
    - [x] Edges: membership, replies, forwards, link mentions
    - [x] Export to multiple formats (GraphML, GEXF, JSON, CSV, PNG)
    - [x] Filter by date, minimum reply count
    - [x] Graph statistics (node/edge types, degrees, bot/premium counts)
- [x] Interactive subscription / communication graph for telegram
- [x] Exporting graphs to JSON, GraphML, GEXF, CSV, PNG, HTML
- [x] Search for email information (which resources were registered on)
  - [x] intelx.io
- [x] Username search (sherlock project db + maigret)
- [x] GitHub OSINT
  - [x] User / repository search
  - [x] Email search in commits
  - [x] Secret scanning (API keys, tokens, passwords)
  - [x] Code dorking (code, commits, issues, repos, users)
- [ ] Reverse Image Search With Yandex and Google

## `SETUP SEARXNG`

To work with dorking, you need to run searxng via docker:

```bash

docker compose up --build

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
