<div align="center">

# `SkyFall Project`

<img src="./resources/icon.png" width="150px"/>

</div>

## `STACK`

- telethon | tg api
- qt | ui
- sqlalchemy | orm
- networkx | graph
- ddgs | duckduckgo
- python3-nmap | nmap integration
- python-whois
- dnspython
- fake_useragent
- ssl
- socket
- ...

## `FUNCTIONAL`

- [ ] Collecting all information about web resources or ip addresses
  - [x] IP info
  - [x] SSL / TLS
  - [x] DNS
  - [x] Headers
  - [x] Server Location
  - [ ] Associated Hosts
  - [x] Open ports (nmap scan 1–65535)
  - [x] WHOIS (registrar, creation/expiration dates, name servers)
  - [x] Web stack (HTTP headers, web server, WAF, detected tech — Nginx, Apache, WordPress, Bitrix, jQuery)
  - [x] WAF
  - [x] Malware reputation (VirusTotal, Google Safe Browsing, CRDF Labs)
  - [x] NMAP (vuln scripts)
- [x] Dorking via duckduckgo
- [ ] Telegram OSINT
  - [ ] User Data Collection
    - [ ] Complete user profiles: ID, username, first name, last name, phone (if available)
    - [ ] Statuses and flags: verification, Telegram Premium, bots, scam/fake accounts
    - [ ] Activity: online/offline status, last seen timestamp
    - [ ] Additional information: bio, language, profile photo
    - [ ] Relationships: mutual contacts, presence in your contacts
  - [ ] Channel Members Collection
    - [ ] Retrieval of all channel/group members
    - [ ] Saving membership data (join date, status)
    - [ ] Integration with global user database
  - [ ] Link Extraction
    - [ ] Automatic extraction of all URLs from messages
    - [ ] Support for Telegram links (t.me, @username)
    - [ ] Saving link context (surrounding text)
    - [ ] Link classification by type (telegram, http, https)
  - [ ] Interaction Graph Analysis
    - [ ] Build interaction graphs from collected data
    - [ ] Nodes: users, channels, domains
    - [ ] Edges: membership, replies, forwards, link mentions
    - [ ] Export to multiple formats (GraphML, GEXF, JSON, CSV, PNG)
    - [ ] Filter by date, minimum reply count
    - [ ] Graph statistics (node/edge types, degrees, bot/premium counts)
- [ ] Creating an interactive subscription graph for user communication in telegram
- [ ] Search for email information (which resources were registered on)
  - [x] intelx.io
- [ ] Username search
  - [ ] Reddit
  - [ ] Telegram
  - [ ] Discord
  - [ ] YT
  - [ ] Pinterest
  - [ ] Leetcode
  - [ ] Linkedin
  - [ ] Medium
  - [ ] VK
  - ...
- [ ] Creating interactive graphs of communication with various data
- [ ] Exporting graphs to JSON or SQL DB

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
