# SkyFall — документация функционала

**SkyFall 1.0.1** — настольный OSINT-инструментарий для проведения цифровых расследований.
Разработан на **Python 3** + **PySide6 (Qt 6)**, интерфейс загружается из `resources/form.ui`.
Автор: Nighty3098.

---

## Содержание

1. [Архитектура](#архитектура)
2. [Установка и запуск](#установка-и-запуск)
3. [Настройки и API-ключи](#настройки-и-api-ключи)
4. [Кейсы (Case Manager)](#кейсы-case-manager)
5. [Вкладки программы](#вкладки-программы)
   - [Telegram Downloader](#telegram-downloader)
   - [Telegram Analyzer](#telegram-analyzer)
   - [Username](#username)
   - [Mail](#mail)
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
6. [Граф (Graph)](#граф-graph)
7. [MCP-серверы](#mcp-серверы)
8. [Структура кода](#структура-кода)
9. [Данные и хранение](#данные-и-хранение)

---

## Архитектура

```
main.py → src/connectors.py (сигналы Qt) → src/controllers/ → src/modules/ (сбор данных)
                                                └── src/libs/ (граф)
                                                └── src/mcp_controller.py, graph_bridge.py
```

- **Контроллеры** (`src/controllers/`) — UI-логика: читают/пишут виджеты, вызывают модули.
- **Модули** (`src/modules/`) — UI-независимый сбор данных через внешние API.
- **Коннекторы** (`src/connectors.py`) — связывают сигналы Qt-виджетов с методами контроллеров.
- **qasync-цикл** — все длительные операции запускаются через `asyncio.ensure_future` / `run_in_executor` / `asyncio.to_thread`.
- **Форматирование вывода** — общие помощники в `src/ui/output_formatter.py`: `divider`, `title`, `section`, `kv`, `bullet`, `line`, `info`, `error`, `end_of`.
- **Хоткеи** (`src/shortcuts.py`): `Ctrl+Tab` / `Ctrl+Shift+Tab` — переключение вкладок, `Ctrl+Shift+b` — показать/скрыть навигацию.

---

## Установка и запуск

```bash
# Клонирование с субмодулями (требуется для txfetch)
git clone https://github.com/Nighty3098/SkyFall --recurse-submodules

# Виртуальное окружение
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt

# Dorking: поднять локальный SearXNG (опционально, для режима SearXNG)
docker compose up --build

# Запуск
python3 main.py
# Режим отладки
python3 main.py -d
```

**Разработка:** `./check.sh` (lint), `./format.sh` (автоформат).

**Telegram:** для работы загрузчика нужно предварительно авторизовать сессию через `setup_telegram.py` (создаёт `tg_session.session`).

---

## Настройки и API-ключи

Все настройки хранятся в `~/.skyfall/settings.json`. Сохраняются кнопкой **Save** на вкладке **Settings**; после сохранения ключи автоматически подхватываются работающими модулями.

| Ключ | Виджет | Назначение |
|---|---|---|
| `path_to_storage` | `pathToStorageEdit` | Каталог хранения данных |
| `tg_api_key` | `tgApiKeyEdit` | Telegram API ID |
| `telegram_api_hash` | `telegramApiHashEdit` | Telegram API Hash |
| `telegram_phone` | `telegramPhoneEdit` | Телефон Telegram-аккаунта |
| `intelligent_x_api_key` | `intelligentXApiKeyEdit` | IntelX (почта, телефон, утечки) |
| `hibp_api_key` | `hibpApiKeyEdit` | Have I Been Pwned |
| `virustotal_api_key` | `virustotalApiKeyEdit` | VirusTotal (домены, файлы) |
| `google_safe_api_key` | `googleSafeApiKeyEdit` | Google Safe Browsing |
| `ipinfo_api_key` | `ipinfoApiKeyEdit` | ipinfo.io геолокация IP |
| `github_token` | `githubTokenEdit` | GitHub PAT (несколько через `;` для ротации) |
| `numverify_api_key` | `numverifyApiKeyEdit` | NumVerify (телефоны) |
| `abstractapi_api_key` | `abstractapiApiKeyEdit` | AbstractAPI (телефоны) |
| `trongrid_api_key` | `trongridApiKeyEdit` | TronGrid (блокчейн) |
| `etherscan_api_key` | `etherscanApiKeyEdit` | Etherscan (Ethereum + Base) |
| `bscscan_api_key` | `bscscanApiKeyEdit` | BscScan (BSC) |
| `tonapi_api_key` | `tonapiApiKeyEdit` | TonAPI (TON) |
| `helius_api_key` | `heliusApiKeyEdit` | Helius (Solana) |
| `light_theme` | `lightThemeCheck` | Светлая тема (`style_light.qss`) |
| `frameless_window` | `framelessCheck` | Окно без рамки |

Дополнительно на вкладке Settings — блок **MCP Server** (`mcpStatusLabel`, `mcpToggleButton`) для запуска/остановки встроенного MCP-сервера.

---

## Кейсы (Case Manager)

`src/case_manager.py` — концепция «кейса» расследования. Меню **SkyFall → New case / Open case**.

- При создании/открытии кейса формируется структура папок: `domains`, `telegram`, `username`, `email`, `github`, `phone`, `mac`, `blockchain`, `files`, `steganography`, `reports`, `dorking` + `graph`.
- **Автосохранение**: содержимое всех debug-панелей автоматически сохраняется в Markdown-файлы с меткой времени (`YYYY-MM-DD_HH-MM-SS_<label>.md`) в соответствующие категории. Повторяющееся (расширенное) содержимое перезаписывает текущий файл вместо создания нового.
- Название кейса отображается в меню SkyFall.
- Каталоги: `<case>/graph`, `<case>/reports` (если кейса нет — `~/.skyfall/data`).

---

## Вкладки программы

### Telegram Downloader

Сбор данных Telegram-канала/группы через MTProto (библиотека Telethon) в SQLite `SkyFall_TG.db`.

**Поля и элементы:**
- `telegramUsernameEdit` — username канала (например, `@channel` или `channel`).
- `telegramUseProxyCheck` — использовать прокси из списка (`~/.skyfall/proxies.txt`).
- **Safety Delays**: `telegramBaseDelay` (пауза между запросами), `telegramMaxReq` (лимит запросов), `telegrammembersDelay` (пауза при сборе участников), `telegramPause` (длительность паузы).
- `telegramDownloadMediaCheck` — скачивать медиафайлы.
- `telegramCollectMembersCheck` — собирать участников канала.
- `telegramCollectLinksCheck` — собирать ссылки из сообщений.
- `telegramMultiAccCheck` — мультиаккаунт (ротация `.session`-файлов).
- `telegramDownloadStart` — запуск сбора.
- `telegramDownloadProgress` — прогресс (стадии: channel / discussion / avatars / done).
- `telegramDownloadAvatarsBtn` — отдельно докачать аватары участников.
- `telegramAccountInfo` — информация об использованном аккаунте.
- `telegramDownloaderDebug` — лог процесса.

**Что собирается:**
- Канал/группа, участники, сообщения (текст, медиа, просмотры, репосты, автор), пересылки (forward), обсуждения (вложенный чат), ссылки из текстов, профили пользователей (включая business-поля и день рождения через `GetFullUserRequest`).
- Медиа в папку `SkyFall_TG_media/<channel>/` (посты и `discussion_<id>/`), аватары в `avatars/<user_id>.jpg`.

**Возможности:**
- Докачка с места остановки (по последнему `post_id`).
- Ротация прокси (MTProto `host:port:secret`, `t.me/proxy`-ссылки, SOCKS4/SOCKS5/HTTP) при ошибках/флуде.
- Автоматический переключение на другой аккаунт при исчерпании лимита запросов.
- Обработка `FloodWaitError` и «умные» паузы.

### Telegram Analyzer

Анализ скачанной БД `SkyFall_TG.db` и построение графа связей.

**Поля и элементы:**
- `telegramAnalyzerLoadChannelsButton` — загрузить список каналов (путь из `pathToStorageEdit` или `~/.skyfall/data`).
- `telegramChannelsList` — выбор каналов (или «All Channels»).
- `includeLinksCheck` — включать связи по ссылкам (узлы `domain:*`).
- `telegramAnalyzerStartDate` / `telegramAnalyzerEndDate` — фильтр по дате постов.
- `telegramAnalyzerMinReplies` — минимальное число ответов для связи user↔user.
- `includeForwardingCheck` — включать связи по пересылкам.
- **Экспорт**: `telegramAnalyzerGraphMLCheck`, `checkBox_7` (GEXF), `telegramAnalyzerJSONCheck`, `telegramAnalyzerCSVCheck`, `checkBox_8` (CSV edges), `telegramAnalyzerPNGCheck`, `telegramAnalyzerHTMLCheck` (интерактивный pyvis), `telegramAnalyzerObsidianCheck` (Obsidian-хранилище).
- `runTelegramAnalyzerBtn` — запуск анализа.
- `telegramAnalyzerProgress`, `telegramAnalyzerDebug`.

**Граф включает:**
- Узлы пользователей, каналов, доменов.
- Рёбра: членство (`member`), ответы (`replier`, взвешенные), пересылки (`forwarded`), ответы в обсуждениях (`discussion_reply`), упоминания (`mentions`), общие участники между каналами (`shared_members`, опционально).
- Статистика: количество узлов/рёбер, степени, боты/верифицированные/premium.

**Форматы экспорта:** GraphML, GEXF, JSON (node-link), CSV (nodes/edges), PNG (matplotlib), HTML (pyvis с панелью информации об узле), Obsidian Markdown (файлы каналов/участников с вики-ссылками и встроенными аватарами).

Кнопка **To Main Graph** (`tgToGraphButton`) пересобирает TG-граф из БД с текущими фильтрами и загружает его в главный граф (`src/modules/graph_io.py`: user→Person, channel→Organization, domain→Domain; member→member_of, replier/discussion_reply→communicates_with, forwarded/mentions/linked_chat→linked_to, shared_members→associated_with; spring-раскладка). Там же работает импорт файлов TG-экспорта и экспорт холста в PNG/SVG.

### Username

Поиск username по сотням сайтов двумя движками.

- `usernameEdit` + `searchUsernameButton` — запуск.
- `usernameSearchProgress` — общий прогресс.
- `maigretDebug` — результат **Maigret** (движок ~510 сайтов, поиск с разбиением на чанки).
- `usernameScriptDebug` — результат **Sherlock-подобного** поиска (встроенная база `data/username_data.json`, ~481 сайт; при отсутствии локальной базы — удалённая `https://data.sherlockproject.xyz`).

Каждый сайт проверяется на занятость username (статусы: CLAIMED / AVAILABLE / UNKNOWN / ILLEGAL / WAF), учитываются WAF-сигнатуры (Cloudflare, AWS WAF, PerimeterX).

### Mail

Поиск по почтовому адресу.

- `mailEdit` — email.
- `startMailSearchButton` — **IntelX** поиск: создание поисковой задачи → опрос результатов → загрузка содержимого bucket'ов. Вывод в `mailSearchDebug`: список баз данных (Found N databases), bucket ID, дата, размер, источник, теги, содержимое.
- `startHibpCheckButton` — **Have I Been Pwned**: список утечек (имя, домен, дата, число скомпрометированных аккаунтов, типы данных). Вывод в `hibpDebug`. Учитывается `Retry-After` при 429.
- `analyzeEmlButton` — **EML / Headers**: выбор `.eml`-файла (или вставка сырых заголовков в `mailEdit`) → разбор в `emailHeaderDebug`: конверт (From/Reply-To/Return-Path/Message-ID), цепочка Received (по хопам с IP), SPF/DKIM/DMARC из `Authentication-Results`, DNS-проверка SPF/DMARC записей домена отправителя, гео IP origin (rDNS + ip-api.com: страна/город/ISP/ASN, флаги proxy/hosting), вердикт LOW/MEDIUM/HIGH.

### Dorking

Google-дорки по базе `data/dorks.json` (14 категорий, ~7 944 дорка; также есть `dorks.xml`).

- `dorksCategoryList` — категория (двойной клик загружает дорки), `dorksCategorySearchEdit` — фильтр.
- `dorksList` — список дорков (двойной клик запускает поиск), `dorksListSearchEdit` — фильтр, контекстное меню «Move to edit».
- `customDorkEdit` + `dorkItButton` — запуск произвольного дорка.
- `useSearxngCheck` — использовать локальный **SearXNG** (`http://localhost:8080`), иначе **DuckDuckGo** (библиотека `ddgs`).
- `useCustomDorkCheck` — использовать пользовательский дорк из поля ввода.
- `dorksResult` — результаты, `dorksResultSearchEdit` — подсветка найденного текста в результатах.

### Web

Полный анализ домена — 14 шагов (выбор чекбоксами, прогресс `domainProgress`).

| Чекбокс | Панель | Что делает |
|---|---|---|
| `domainRobotsCheck` | `serverRobotsDebug` | robots.txt |
| `domainLocationCheck` | `serverLocationDebug` | IP + геолокация (ipapi.co, ip-api.com, ipinfo.io) |
| `domainSSLCheck` | `serverTlsDebug` | SSL/TLS сертификат (версия, шифр, эмитент, срок) |
| `domainDNSCheck` | `serverDnsAnalyzeDebug` | DNS: A/MX/TXT/NS/CNAME/SOA + IP-адреса NS + стандартные хосты |
| `domainHeadersCheck` | `serverWafDebug` | HTTP-заголовки, веб-сервер, WAF, стек технологий |
| `domainWhoisCheck` | `serverWhoisDebug` | WHOIS |
| `domainNmapCheck` | `serverNmapDebug` | NMAP-скан портов 1-1024 (`--script=vuln`, нужен системный nmap) |
| `domainMalwareCheck` | `serverMalwareDebug` | Репутация: VirusTotal → Google Safe Browsing → CRDF Labs |
| `domainSubdomainsCheck` | `serverSubdomainsDebug` | Субдомены через DuckDuckGo (`site:domain`) |
| `securityTxtCheck` | `securityTxtDebug` | `/.well-known/security.txt` |
| `cookiesCheck` | `cookiesDebug` | Cookies сайта |
| `socialTagsCheck` | `socialTagsDebug` | OpenGraph / Twitter мета-теги |
| `certTrCheck` | `certTrDebug` | Certificate Transparency через crt.sh |
| `domainsOnIpCheck` | `domainsOnIpDebug` | Обратный поиск: домены на IP (PTR, Shodan InternetDB, HackerTarget) |

Дополнительно: `serverUrlEdit` + `runUrlScanButton` — указать домен и запустить анализ.

### File Analyze

Анализ файла (перетаскиванием в `metadataFileDropWidget` или кнопкой `getMetadataButton`).

- `fileMetadataCheck` → `metadataDebug`: метаданные (размер, MIME, хэши MD5/SHA-256, временные метки, права, Hachoir-дамп) + проверка на «хвост» после конца файла (`check_tail_data`). При наличии GPS-координат — карта Leaflet в `metadataMapView` (OpenStreetMap, маркер по координатам).
- `fileStringsCheck` → `stringsFileDebug`: печатаемые ASCII-строки (min_len=4).
- `fileVirustotalCheck` → `virustotalFileDebug`: VirusTotal — проверка по SHA-256; если файл не найден — загрузка на сканирование (до 650 МБ, крупные файлы через большой upload URL) и ожидание результата.
- `cleanMetadataButton` — удаление метаданных из файла на месте (см. модуль `metadata_cleaner`), затем повторный анализ.

**Удаление метаданных поддерживает:** ZIP (рекурсивно все записи), JPEG/PNG/GIF/BMP/TIFF, PDF, DOCX, PPTX, ODT/ODS, EPUB, RTF, MP3, FLAC, XLSX.

### GitHub

Поиск по GitHub REST API. Поле `githubTokenEdit` (PAT; несколько токенов через `;` — автоматическая ротация при лимитах).

- `githubUserEdit` + `githubUserSearchBtn` — профиль пользователя + его репозитории (top-15 по обновлению).
- `githubRepoEdit` + `githubRepoSearchBtn` — поиск репозиториев (язык, звёзды, форки, описание).
- `githubCommitEdit` + `githubCommitSearchBtn` — поиск коммитов (по username/repo или любому запросу).
- `githubEmailEdit` + `githubEmailSearchBtn` — поиск email в коде (`<query> email OR @ OR .com`).
- `githubSecretEdit` + `githubSecretSearchBtn` — поиск секретов: обход ~240 паттернов секретов (ключи API, SSH, AWS/Azure/GCP, БД-строки, Stripe, GitHub/GitLab токены, Slack, OpenAI, Twilio, Docker/K8s, JWT/OAuth и т.д.). Прогресс по паттернам в `githubProgress`.
- `githubDorkEdit` + `githubDorkSearchBtn` + `githubDorkGroup` — произвольный GitHub-дорк по типу: code / commits / issues / repositories / users.
- Результаты — в `githubDebug` с прогрессом и остатком лимитов (`[Page N] Rate: r/lim`).

### Phone

Анализ телефонного номера.

- `phoneNumberEdit` — номер; `phoneRegionEdit` — регион по умолчанию (например `RU`).
- `phoneParseBtn` → `parse_validate`: парсинг/валидация (phonenumbers): форматы, код страны, регион, тип, оператор, геолокация, часовые пояса.
- `phoneLookupBtn` → `reverse_lookup`: обратный поиск через **NumVerify** и **AbstractAPI** (требуются ключи).
- `phoneLeakBtn` → `check_leaks`: утечки через **IntelX** (поиск → ожидание → результаты + содержимое bucket'ов).
- `phone7telBtn` → `search_7tel`: отзывы/рейтинг на **7tel.ru** (без ключей; скрапинг: оценка, число негативных отзывов, список отзывов, похожие номера).
- `phoneProgress`, `phoneDebug` — прогресс и вывод.

### MAC Addr

Геолокация MAC-адреса (BSSID) по пяти провайдерам: **Yandex, Apple, Google, Microsoft, Mylnikov** (протоколы — неофициальные: XML/Protobuf).

- `macAddrEdit` + `checkMacAddrButton` — запуск.
- `macAddrLocationDebug` — координаты по каждому провайдеру.
- `macLocationMapView` — карта Leaflet со всеми найденными координатами.

### Blockchain

Поиск транзакций по косвенным данным (сумма, время, сеть, memo) через встроенную библиотеку **txfetch** (thirdparty).

- `bcNetworkCombo` — сеть: Tron, TON, Ethereum, BSC, Base, Solana, Bitcoin, Litecoin, Dogecoin, Bitcoin Cash.
- `bcCoinCombo` — монета.
- `bcDateEdit` — дата или диапазон (`ДД.ММ.ГГГГ` / `ДД.ММ.ГГГГ-ДД.ММ.ГГГГ`).
- `bcTimeEdit` — время (`ЧЧ:ММ[:СС]`).
- `bcTimeRangeCombo` — точность: exact / ±1 min / ±5 min / ±15 min / custom.
- `bcAmountEdit` — сумма или диапазон `min-max`.
- `bcToleranceSpin` — допуск по сумме (доли).
- `bcMemoEdit` — memo (для TON).
- `bcSearchButton` + `bcProgressBar` — запуск; результаты в `bcDebug`: tx_id, уверенность %, время, сумма/монета, разбор оценки Δt/ΔA/ΔT/M, адреса от/до, memo.

**Ключи:** TronGrid, Etherscan (ETH+Base), BscScan, TonAPI, Helius (Solana). BTC/LTC/DOGE/BCH — публичные ноды без ключей.

### Steganography

Анализ изображений на скрытые данные (перетаскивание в `steganoFileDrop`).

- `LSBDebug` — **LSB-анализ**: счётчики битов по каналам R/G/B/A, соотношения, хи-квадрат тест, проверка уникальности альфа-канала, оценка ёмкости.
- `spectralAnalysisDebug` — **спектральный анализ** (FFT): энергия низких/высоких частот, отношения, дисперсия средних частот и диагоналей, аномалии.
- `EOIDebug` — **конец файла** (EOI/EOD): поиск «хвоста» после маркеров PNG/JPEG/GIF/BMP/TIFF/WebP, hex-дамп и идентификация содержимого (ZIP, GZIP, RAR, ELF, PE, PDF, SQLite, HTML, URL и т.д.).
- `tailDataDetectionDebug` — общее детектирование скрытых данных в конце файла.
- `elaDebug` — **ELA (Error Level Analysis)**: пережатие в JPEG Q=90, разница с оригиналом, статистика (mean/std/p95, доля hot-пикселей, hot 8x8-блоков), heatmap сохраняется рядом как `<имя>_ela.png`, вердикт (uniform / localized edit / resaved).

### Search4Faces

Обратный поиск по лицу через сервис **search4faces.com** (VK-фотографии; скрапинг приватных AJAX-эндпоинтов).

- `s4fFileDrop` — перетащить фото лица (отображается в `s4fTargetLabel`).
- `runS4FButton` — запуск поиска.
- Результаты — карточки `S4FResultWidget` в `s4fResultsScrollArea`: миниатюра лица, имя/фамилия, возраст, город, страна, сходство %, ссылка на VK.
- `s4fSearchEdit` — поиск по профилям в результатах (Enter — переход к следующему совпадению).

### Graph

Визуальный граф связей с палитрой сущностей (`entityPalette`, перетаскивание на холст) и панелью редактирования узла.

- `entitySearchEdit` — фильтр палитры.
- `graphWidget` — холст (см. [Граф](#граф-graph)).
- `exportGraphButton` / `importGraphButton` — сохранение/загрузка JSON-графа; импорт также понимает экспорты TG Analyzer (GraphML/GEXF/node-link JSON/CSV-пара) с маппингом сущностей и автораскладкой.
- `exportGraphImageButton` — экспорт холста в PNG (x2) / SVG.
- `graphClearButton` — очистить граф.
- `graphLayoutCombo` + `graphAutoLayoutButton` — автоматическая раскладка (spring / kamada_kawai / shell / spectral / circular).
- `graphSearchEdit` + `graphClearFilterButton` + `graphFilterCombo` — фильтрация по тексту и типу сущности.
- Панель узла: `nodeTitleEdit`, `nodeTypeCombo`, `nodeContentEdit`, `nodeEvidenceList`, `nodeEvidenceAddFileBtn`, `nodeEvidenceAddUrlBtn`, `nodeEvidenceRemoveBtn`.

### AI Report

Генерация итогового OSINT-отчёта через локальную **Ollama** (MCP-сервер `ollama_mcp_server.py`).

- `updateOllamaListButton` + `ollamaModelsSelector` — список моделей из Ollama (`http://127.0.0.1:11434`).
- `aiReportLangEdit` — язык отчёта (по умолчанию `Russian`).
- `generateReportButton` — сбор всех результатов (~28 debug-панелей + данные графа + поисковые входные данные) и генерация структурированного отчёта (7 секций, маркеры достоверности `[FACT]/[INFERRED]/[HYPOTHESIS]`).
- `saveReportButton` — сохранить отчёт в Markdown (`<case>/reports/`).

### Settings

См. [Настройки и API-ключи](#настройки-и-api-ключи). Также блок **MCP Server**: `mcpStatusLabel` + `mcpToggleButton` — запуск/остановка встроенного MCP-сервера (SSE на `127.0.0.1:9877`).

### Proxy

- `proxyListEdit` — список прокси (по одному в строку); `saveProxiesButton` — сохранить в `~/.skyfall/proxies.txt`.
- Форматы: `t.me/proxy?...`, `tg://proxy?...`, `type://host:port`, MTProto `host:port:secret` / `secret@host:port`, `user:password@host:port` (SOCKS4/SOCKS5/HTTP).

---

## Граф (Graph)

### Сущности (13 типов)

| Тип | Цвет | Символ |
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

### Связи (12 типов)

`owns`, `registered_at`, `resolved_to`, `member_of`, `located_at`, `communicates_with`, `associated_with`, `works_at`, `created_by`, `attends`, `hosted_by`, `linked_to`.

Стили рёбер: `normal` (сплошная), `dashed` (пунктир), `bold` (утолщённая). Рёбра — кубические кривые Безье со стрелкой, чипом типа связи и необязательной подписью.

### Возможности холста

- Узлы: перемещение, изменение размера (ручка в углу), перетаскивание портов для создания рёбер, двойной клик — диалог редактирования.
- **Photo-узлы** — галерея миниатюр из файлов/URL (с кешированием и `+N` бейджем).
- **Geolocation-узлы** — встроенная карта (мозаика OpenStreetMap, zoom 5–18, маркер, Ctrl+колесо для зума).
- Контекстное меню: редактирование узла/ребра, стиль ребра, прикрепление улик, цвет, удаление; **Analysis** — кратчайший путь (по клику), центральность степени (масштабирование узлов + top-5), обнаружение сообществ (greedy modularity).
- **⚡ Transforms** (обогащение графа, `graph_transform_controller`): из узла строятся дочерние узлы-результаты поиска, расположенные дугой:
  - **Username** → поиск соцсетей, Maigret;
  - **Domain** → IP, DNS, SSL/TLS, веб-стек, WHOIS, субдомены, Certificate Transparency, соц-теги, репутация, security.txt, cookies, robots.txt, порты;
  - **IP** → геолокация, порты, домены на IP;
  - **Email** → IntelX;
  - **Phone** → парсинг, обратный поиск, утечки;
  - **MAC** → геолокация.
- Персистентность: JSON (`to_dict`/`from_dict`, `save_to_json`/`load_from_json`).

---

## MCP-серверы

### SkyFall MCP Server (`src/skyfall_mcp_server.py`) — 66 инструментов

Сервер FastMCP: `--host 127.0.0.1 --port 9877`, транспорты `stdio`/`sse`. Запускается/останавливается с вкладки Settings (кнопка MCP) или через `McpController`.

**Ollama (4):** список моделей, установить/получить модель, установить URL.

**Домены (14):** ip, домены на IP, DNS, WHOIS, SSL, заголовки, веб-стек, nmap, WAF, репутация, субдомены, robots.txt, security.txt, соц-теги.

**Username (2):** sherlock-поиск (`skyfall_username_search`), maigret (`skyfall_maigret_search`).

**Email (5):** IntelX, HIBP, комбинированный, разбор `.eml`-файла, разбор вставленных заголовков.

**Телефоны (5):** парсинг, обратный поиск, утечки, полный, 7tel.

**GitHub (6):** user, repo, commits, emails, secrets, dork.

**Блокчейн (1):** поиск транзакций по 10 сетям.

**MAC (1):** геолокация по провайдерам.

**Файлы (5):** инфо, метаданные, VirusTotal, tail-data, строки.

**Стеганография (6):** lsb, spectral, eoi, tail, ela, full.

**Доркинг (1):** поиск через DuckDuckGo/SearXNG.

**Граф (12, требуют запущенного GUI + graph bridge на 127.0.0.1:9878):** add/update/remove/move node, add/remove edge, get, summary, get_node, clear, import файла (JSON/GraphML/GEXF/CSV), export PNG/SVG.

**Кейсы (2):** список кейсов, содержимое кейса.

**Отчёт (1):** генерация OSINT-отчёта через Ollama.

**Лица (1):** поиск по photo через search4faces.

Ресурсы: `skyfall://modules` (обзор инструментов), `skyfall://settings` (замаскированные ключи).

### Ollama OSINT Reporter (`src/ollama_mcp_server.py`) — 6 инструментов

Stdio-транспорт, Ollama `http://127.0.0.1:11434`, модель по умолчанию `hf.co/OBLITERATUS/Gemma-4-12B-OBLITERATED:Q8_0`.

- `set_ollama_url`, `get_ollama_model`, `set_ollama_model`, `list_ollama_models`, `generate_osint_report(data, language)` (строгий системный промпт на 250 строк: типизация IDENTIFIER/INFRASTRUCTURE/GEOLOCATION/CONNECTION, маркеры достоверности, фильтры шума, 7-секционная структура отчёта), `skyfall_s4f_search`.

### Graph Bridge (`src/graph_bridge.py`)

TCP-мост `127.0.0.1:9878`, протокол: 4-байтовый длинный префикс (big-endian) + JSON. Действия: `add_node`, `add_edge`, `get_graph`, `get_node`, `update_node`, `move_node`, `remove_node`, `remove_edge`, `clear_graph`, `graph_summary`. Все операции маршалируются в поток GUI через Qt-сигнал (thread-safe).

---

## Структура кода

```
main.py                     — точка входа, загрузка UI, инициализация модулей/контроллеров
setup_telegram.py           — авторизация Telegram-сессии
logger_setup.py             — настройка логгера (loguru)
src/
  connectors.py             — связывание сигналов Qt с контроллерами
  case_manager.py           — кейсы расследований, автосохранение
  report_controller.py      — AI-отчёт через Ollama
  mcp_controller.py         — жизненный цикл MCP-сервера + graph bridge
  graph_bridge.py           — TCP-мост GUI-графа для MCP
  context_menus.py          — контекстные меню (дворки)
  shortcuts.py              — глобальные хоткеи
  utils.py                  — фильтрация списков, подсветка текста
  searxng_search.py         — клиент локального SearXNG
  modules/                  — сбор данных (UI-независимо)
    tg/                     — пакет Telegram: db, models, proxy, throttler,
                              client_manager, session_manager, users, cache, extractors, state
  controllers/              — UI-логика по вкладкам
  libs/                     — graph_lib (граф), graph_panel (палитра)
  ui/                       — setup_ui, drop_widget, output_formatter, s4f_result_widget
resources/                  — form.ui, QSS-темы, шрифты, иконки
data/                       — dorks.json, dorks.xml, username_data.json
thirdparty/txfetch/         — вендоренная библиотека поиска транзакций
```

---

## Данные и хранение

- **`~/.skyfall/`**: `settings.json` (настройки/ключи), `proxies.txt`, `logs/`, `data/` (кейсы, `SkyFall_TG.db`, `SkyFall_TG_media/`, графы).
- **`data/dorks.json`** — 14 категорий, ~7 944 дорка. **`data/dorks.xml`** — исходная база GHDB.
- **`data/username_data.json`** — 481 спецификация сайта для username-поиска (шаблоны URL, коды ошибок, regex).
- **`resources/form.ui`** — UI (2624 строки), загружается в рантайме.
- **БД Telegram** — SQLite `SkyFall_TG.db`: таблицы `channels`, `users`, `posts`, `discussions`, `members`, `links`.

---

## Внешние сервисы (сводно)

| Сервис | Где используется | Нужен ключ |
|---|---|---|
| Telegram MTProto | загрузчик/анализатор | API ID/Hash + сессия |
| IntelX public API | email, phone leaks, username | `intelligent_x_api_key` |
| Have I Been Pwned | email | `hibp_api_key` |
| VirusTotal API v3 | домены, файлы | `virustotal_api_key` |
| Google Safe Browsing | репутация домена | `google_safe_api_key` |
| ipinfo.io / ipapi.co / ip-api.com | геолокация IP | ipinfo — опционально |
| GitHub REST API | поиск | `github_token` |
| NumVerify / AbstractAPI | телефоны | `numverify` / `abstractapi` |
| 7tel.ru | телефоны (отзывы) | нет |
| search4faces.com | лица | нет |
| Yandex / Apple / Google / Microsoft / Mylnikov | MAC-геолокация | нет |
| crt.sh | Certificate Transparency | нет |
| Shodan InternetDB / HackerTarget | домены на IP | нет |
| CRDF Labs | репутация домена (fallback) | нет |
| DuckDuckGo (ddgs) | дорки, субдомены | нет |
| SearXNG (локальный) | дорки | нет |
| Ollama | AI-отчёт | локально |
| txfetch (TronGrid/Etherscan/BscScan/TonAPI/Helius) | блокчейн | да |
| Maigret | username | нет |

**Лицензия:** MIT (см. `LICENSE`, `THIRD_PARTY_NOTICES.md`).
