from collections.abc import Callable

import httpx
from loguru import logger

from src.ui.output_formatter import error, kv, section, title

SECRET_PATTERNS = [
    "api_key",
    "api-key",
    "apikey",
    "api_secret",
    "api-secret",
    "apisecret",
    "secret_key",
    "secret-key",
    "secretkey",
    "password",
    "passwd",
    "token",
    "bearer",
    "authorization",
    "auth_token",
    "auth-token",
    "authtoken",
    "ssh-rsa",
    "ssh-dsa",
    "-----BEGIN",
    "client_secret",
    "client-secret",
    "clientsecret",
    "aws_access_key",
    "aws_secret_key",
    "aws-key",
    "AKIA",
    "sk_live",
    "pk_live",
    "ghp_",
    "gho_",
    "ghu_",
    "ghs_",
    "ghr_",
    "xox[apbors]-",
    "mongodb",
    "mysql://",
    "postgres://",
    "redis://",
    "slack_token",
    "slack-token",
    "slacktoken",
]

SEARCH_QUERIES = {
    "filename:.env": "filename:.env",
    "filename:.env.example": "filename:.env.example",
    "filename:config.json": "filename:config.json",
    "filename:credentials": "filename:credentials",
    "filename:secrets": "filename:secrets.yml OR filename:secrets.yaml",
    "filename:id_rsa": "filename:id_rsa",
    "filename:id_dsa": "filename:id_dsa",
}


class GitHubSearch:
    def __init__(self, token: str = ""):
        logger.debug("Init: GitHubSearch")
        self._token = token
        self._base = "https://api.github.com"
        self._headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "SkyFall-OSINT/1.0",
        }
        if token:
            self._headers["Authorization"] = f"Bearer {token}"

    def _rate_limit_remaining(self, resp: httpx.Response) -> tuple[int, int]:
        remaining = int(resp.headers.get("X-RateLimit-Remaining", 0))
        limit = int(resp.headers.get("X-RateLimit-Limit", 60))
        return remaining, limit

    async def search_emails(
        self,
        query: str,
        on_result: Callable | None = None,
        on_progress: Callable | None = None,
    ) -> str:
        results = []
        q = f"{query} email OR @ OR .com"
        page = 1
        per_page = 100

        while True:
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.get(
                        f"{self._base}/search/code",
                        params={"q": q, "per_page": per_page, "page": page},
                        headers=self._headers,
                    )

                if resp.status_code == 403:
                    results.append(
                        f"\n{error('Rate limited. Add GitHub token in settings.')}"
                    )
                    break
                if resp.status_code != 200:
                    results.append(f"\n{error(f'API error {resp.status_code}')}")
                    break

                data = resp.json()
                items = data.get("items", [])
                if not items:
                    break

                remaining, limit = self._rate_limit_remaining(resp)
                if on_progress:
                    on_progress(page, remaining, limit)

                for item in items:
                    repo = item["repository"]["full_name"]
                    path = item["path"]
                    url = item["html_url"]
                    entry = f"[{repo}] {path}\n  {url}"
                    results.append(entry)
                    if on_result:
                        on_result(entry)

                page += 1
                if data.get("total_count", 0) < page * per_page:
                    break

            except httpx.RequestError as e:
                results.append(f"\n{error(f'Request failed: {e}')}")
                break

        if not results:
            return "No email results found."

        header = f"{title(f'Email search results for {query!r}:')}\n"
        return header + "\n".join(results)

    async def search_secrets(
        self,
        query: str,
        pattern_filter: list[str] | None = None,
        on_result: Callable | None = None,
        on_progress: Callable | None = None,
    ) -> str:
        results = []
        patterns = pattern_filter or SECRET_PATTERNS
        total = len(patterns)
        done = 0

        for pattern in patterns:
            done += 1
            q = f"{query} {pattern}"
            if on_progress:
                on_progress(done, total, pattern)

            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.get(
                        f"{self._base}/search/code",
                        params={"q": q, "per_page": 5},
                        headers=self._headers,
                    )

                if resp.status_code == 401:
                    results.append(
                        "\n"
                        + error("Bad credentials. Check your GitHub token in settings.")
                    )
                    if on_result:
                        on_result(results[-1])
                    break
                if resp.status_code == 403:
                    body = resp.json()
                    msg = body.get("message", "Rate limited")
                    results.append(f"\n{error(msg)}")
                    if on_result:
                        on_result(results[-1])
                    break
                if resp.status_code != 200:
                    continue

                data = resp.json()
                items = data.get("items", [])
                if not items:
                    continue

                results.append(f"\n{section(pattern)}")
                if on_result:
                    on_result(f"\n{section(pattern)}")

                for item in items[:3]:
                    repo = item["repository"]["full_name"]
                    path = item["path"]
                    url = item["html_url"]
                    entry = f"  [{repo}] {path}\n    {url}"
                    results.append(entry)
                    if on_result:
                        on_result(entry)

            except httpx.RequestError:
                continue

        if not results:
            return "No secrets found."

        return f"{title(f'Secret scan results for {query!r}:')}" + "\n".join(results)

    async def search_commits(
        self,
        query: str,
        on_result: Callable | None = None,
        on_progress: Callable | None = None,
    ) -> str:
        results = []
        q = query.strip()
        page = 1
        per_page = 50

        if "/" in q and " " not in q and q.count("/") == 1:
            owner, repo = q.split("/")
            api_url = f"{self._base}/repos/{owner}/{repo}/commits"
            params = {"per_page": per_page, "page": page}

            while True:
                try:
                    async with httpx.AsyncClient(timeout=30) as client:
                        resp = await client.get(
                            api_url, params=params, headers=self._headers
                        )

                    if resp.status_code == 403:
                        results.append(f"\n{error('Rate limited.')}")
                        break
                    if resp.status_code == 404:
                        results.append(f"\n{error(f'Repo {q!r} not found.')}")
                        break
                    if resp.status_code != 200:
                        results.append(f"\n{error(f'API error {resp.status_code}')}")
                        break

                    items = resp.json()
                    if not items:
                        break

                    if on_progress:
                        on_progress(page, 0, 0)

                    for item in items:
                        author = item.get("commit", {}).get("author", {})
                        email = author.get("email", "N/A")
                        name = author.get("name", "N/A")
                        date = author.get("date", "").split("T")[0]
                        msg = item.get("commit", {}).get("message", "").split("\n")[0]
                        sha = item["sha"][:8]
                        url = item["html_url"]
                        entry = (
                            f"[{sha}] {date} {name} <{email}>\n  {msg} | {q}\n  {url}"
                        )
                        results.append(entry)
                        if on_result:
                            on_result(entry)

                    page += 1
                    params["page"] = page

                    link = resp.headers.get("Link", "")
                    if 'rel="next"' not in link:
                        break

                except httpx.RequestError as e:
                    results.append(f"\n{error(f'Request failed: {e}')}")
                    break
        else:
            if "repo:" not in q and "org:" not in q and "user:" not in q:
                q = f"{q} sort:author-date"

            while True:
                try:
                    async with httpx.AsyncClient(timeout=30) as client:
                        resp = await client.get(
                            f"{self._base}/search/commits",
                            params={
                                "q": f"{q}",
                                "per_page": per_page,
                                "page": page,
                            },
                            headers={
                                **self._headers,
                                "Accept": "application/vnd.github.cloak-preview",
                            },
                        )

                    if resp.status_code == 403:
                        results.append(f"\n{error('Rate limited.')}")
                        break
                    if resp.status_code != 200:
                        results.append(f"\n{error(f'API error {resp.status_code}')}")
                        break

                    data = resp.json()
                    items = data.get("items", [])
                    if not items:
                        break

                    remaining, limit = self._rate_limit_remaining(resp)
                    if on_progress:
                        on_progress(page, remaining, limit)

                    for item in items:
                        author = item.get("commit", {}).get("author", {})
                        email = author.get("email", "N/A")
                        name = author.get("name", "N/A")
                        date = author.get("date", "").split("T")[0]
                        msg = item.get("commit", {}).get("message", "").split("\n")[0]
                        repo = item["repository"]["full_name"]
                        sha = item["sha"][:8]
                        url = item["html_url"]
                        entry = (
                            f"[{sha}] {date} {name} <{email}>\n"
                            f"  {msg} | {repo}\n  {url}"
                        )
                        results.append(entry)
                        if on_result:
                            on_result(entry)

                    page += 1
                    if data.get("total_count", 0) < page * per_page:
                        break

                except httpx.RequestError as e:
                    results.append(f"\n{error(f'Request failed: {e}')}")
                    break

        if not results:
            return "No commits found."

        return f"{title(f'Commit search results for {query!r}:')}\n" + "\n".join(
            results
        )

    async def search_repos(
        self,
        query: str,
        on_result: Callable | None = None,
        on_progress: Callable | None = None,
    ) -> str:
        results = []
        page = 1
        per_page = 50

        while True:
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.get(
                        f"{self._base}/search/repositories",
                        params={"q": query, "per_page": per_page, "page": page},
                        headers=self._headers,
                    )

                if resp.status_code == 403:
                    results.append(f"\n{error('Rate limited.')}")
                    break
                if resp.status_code != 200:
                    results.append(f"\n{error(f'API error {resp.status_code}')}")
                    break

                data = resp.json()
                items = data.get("items", [])
                if not items:
                    break

                remaining, limit = self._rate_limit_remaining(resp)
                if on_progress:
                    on_progress(page, remaining, limit)

                for item in items:
                    full_name = item["full_name"]
                    desc = item.get("description") or "No description"
                    stars = item["stargazers_count"]
                    forks = item["forks_count"]
                    lang = item.get("language") or "N/A"
                    url = item["html_url"]
                    entry = (
                        f"[{full_name}] {lang} | {stars}★ {forks}⑃\n  {desc}\n  {url}"
                    )
                    results.append(entry)
                    if on_result:
                        on_result(entry)

                page += 1
                if data.get("total_count", 0) < page * per_page:
                    break

            except httpx.RequestError as e:
                results.append(f"\n{error(f'Request failed: {e}')}")
                break

        if not results:
            return "No repositories found."

        return f"{title(f'Repository search results for {query!r}:')}\n" + "\n".join(
            results
        )

    async def search_user(
        self,
        username: str,
        on_result: Callable | None = None,
    ) -> str:
        lines = []

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"{self._base}/users/{username}",
                    headers=self._headers,
                )

                if resp.status_code == 403:
                    return error("Rate limited.")
                if resp.status_code == 404:
                    return error(f"User '{username}' not found.")
                if resp.status_code != 200:
                    return error(f"API error {resp.status_code}")

                data = resp.json()
                fields = [
                    ("Login", "login"),
                    ("Name", "name"),
                    ("Company", "company"),
                    ("Blog", "blog"),
                    ("Email", "email"),
                    ("Bio", "bio"),
                    ("Twitter", "twitter_username"),
                    ("Location", "location"),
                    ("Public repos", "public_repos"),
                    ("Followers", "followers"),
                    ("Following", "following"),
                    ("Created", "created_at"),
                    ("Type", "type"),
                    ("Hireable", "hireable"),
                ]
                for label, key in fields:
                    val = data.get(key)
                    if val is not None and val != "":
                        entry = kv(label, val)
                        lines.append(entry)
                        if on_result:
                            on_result(entry)

                resp2 = await client.get(
                    f"{self._base}/users/{username}/repos",
                    params={"per_page": 30, "sort": "updated"},
                    headers=self._headers,
                )
                if resp2.status_code == 200:
                    repos = resp2.json()
                    if repos:
                        lines.append(
                            f"\n{section(f'Recent repos ({len(repos)} shown)')}"
                        )
                        if on_result:
                            on_result(
                                f"\n{section(f'Recent repos ({len(repos)} shown)')}"
                            )
                        for r in repos[:15]:
                            entry = f"  {r['full_name']} ({r.get('language') or 'N/A'})"
                            lines.append(entry)
                            if on_result:
                                on_result(entry)

        except httpx.RequestError as e:
            return error(f"Request failed: {e}")

        return "\n".join(lines)

    async def search_dork(
        self,
        query: str,
        dork_type: str = "code",
        on_result: Callable | None = None,
        on_progress: Callable | None = None,
    ) -> str:
        results = []
        page = 1
        per_page = 50

        api_paths = {
            "code": f"{self._base}/search/code",
            "commits": f"{self._base}/search/commits",
            "issues": f"{self._base}/search/issues",
            "repositories": f"{self._base}/search/repositories",
            "users": f"{self._base}/search/users",
        }

        api_url = api_paths.get(dork_type, f"{self._base}/search/code")
        accept_header = "application/vnd.github.v3+json"
        if dork_type == "commits":
            accept_header = "application/vnd.github.cloak-preview"

        while True:
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.get(
                        api_url,
                        params={"q": query, "per_page": per_page, "page": page},
                        headers={**self._headers, "Accept": accept_header},
                    )

                if resp.status_code == 403:
                    results.append(
                        f"\n{error('Rate limited. Add GitHub token in settings.')}"
                    )
                    break
                if resp.status_code != 200:
                    results.append(f"\n{error(f'API error {resp.status_code}')}")
                    break

                data = resp.json()
                items = data.get("items", [])
                if not items:
                    break

                remaining, limit = self._rate_limit_remaining(resp)
                if on_progress:
                    on_progress(page, remaining, limit)

                for item in items:
                    if dork_type == "code":
                        repo = item["repository"]["full_name"]
                        path = item["path"]
                        url = item["html_url"]
                        entry = f"[{repo}] {path}\n  {url}"
                    elif dork_type == "commits":
                        author = item.get("commit", {}).get("author", {})
                        email = author.get("email", "N/A")
                        name = author.get("name", "N/A")
                        msg = item.get("commit", {}).get("message", "").split("\n")[0]
                        repo = item["repository"]["full_name"]
                        sha = item["sha"][:8]
                        url = item["html_url"]
                        entry = f"[{sha}] {name} <{email}> | {repo}\n  {msg}\n  {url}"
                    elif dork_type == "issues":
                        repo = item["repository"]["full_name"]
                        title = item["title"]
                        state = item["state"]
                        url = item["html_url"]
                        entry = f"[{repo}] [{state}] {title}\n  {url}"
                    elif dork_type == "repositories":
                        full_name = item["full_name"]
                        desc = item.get("description") or "No description"
                        stars = item["stargazers_count"]
                        lang = item.get("language") or "N/A"
                        url = item["html_url"]
                        entry = f"[{full_name}] {lang} | {stars}★\n  {desc}\n  {url}"
                    elif dork_type == "users":
                        login = item["login"]
                        uid = item["id"]
                        url = item["html_url"]
                        entry = f"[{login}] (id: {uid})\n  {url}"
                    else:
                        entry = str(item)

                    results.append(entry)
                    if on_result:
                        on_result(entry)

                page += 1
                total = data.get("total_count", 0)
                if total < page * per_page:
                    break

            except httpx.RequestError as e:
                results.append(f"\n{error(f'Request failed: {e}')}")
                break

        if not results:
            return "No results found."

        return f"{title(f'Dork results for {query!r} ({dork_type}):')}\n" + "\n".join(
            results
        )
