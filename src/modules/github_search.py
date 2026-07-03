from collections.abc import Callable

import httpx
from loguru import logger

from src.ui.output_formatter import (
    bullet,
    divider,
    end_of,
    error,
    info,
    kv,
    section,
    title,
)

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
    "pwd",
    "token",
    "bearer",
    "authorization",
    "auth_token",
    "auth-token",
    "authtoken",
    "client_secret",
    "client-secret",
    "clientsecret",
    "client_id",
    "client-id",
    "clientid",
    "access_token",
    "access-token",
    "accesstoken",
    "refresh_token",
    "refresh-token",
    "refreshtoken",
    "private_key",
    "private-key",
    "privatekey",
    "public_key",
    "public-key",
    "publickey",
    "shared_secret",
    "shared-secret",
    "sharedsecret",
    "signing_key",
    "signing-key",
    "signingkey",
    "encryption_key",
    "encryption-key",
    "encryptionkey",
    # ---- SSH ----
    "ssh-rsa",
    "ssh-dsa",
    "ssh-ed25519",
    "-----BEGIN",
    "-----BEGIN RSA PRIVATE KEY-----",
    "-----BEGIN OPENSSH PRIVATE KEY-----",
    "-----BEGIN DSA PRIVATE KEY-----",
    "-----BEGIN EC PRIVATE KEY-----",
    "-----BEGIN PGP PRIVATE KEY BLOCK-----",
    # ---- AWS (Amazon Web Services) ----
    "aws_access_key_id",
    "aws_secret_access_key",
    "aws_session_token",
    "aws_default_region",
    "aws_access_key",
    "aws_secret_key",
    "aws-key",
    "aws_key",
    "aws_secret",
    "AKIA",
    "ASIA",
    "AWS_ACCESS_KEY",
    "AWS_SECRET_KEY",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "AWS_REGION",
    # ---- Azure ----
    "azure_client_id",
    "azure_client_secret",
    "azure_tenant_id",
    "azure_subscription_id",
    "azure_storage_connection_string",
    "AZURE_CLIENT_ID",
    "AZURE_CLIENT_SECRET",
    "AZURE_TENANT_ID",
    "AZURE_SUBSCRIPTION_ID",
    # ---- Google Cloud Platform (GCP) ----
    "gcp_service_account",
    "google_application_credentials",
    "gcp_project_id",
    "google_credentials",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "GCLOUD_PROJECT",
    "GCP_PROJECT",
    # ---- DB ----
    "mongodb",
    "mysql",
    "postgres",
    "redis",
    "elasticsearch",
    "cassandra",
    "dynamodb",
    "firestore",
    "rethinkdb",
    "mysql://",
    "postgres://",
    "postgresql://",
    "mongodb://",
    "redis://",
    "elasticsearch://",
    "DATABASE_URL",
    "DB_URL",
    "DB_CONNECTION_STRING",
    "MYSQL_URL",
    "POSTGRES_URL",
    "MONGODB_URI",
    "REDIS_URL",
    # ---- Stripe ----
    "stripe_secret_key",
    "stripe_publishable_key",
    "stripe_webhook_secret",
    "stripe_api_key",
    "sk_live_",
    "pk_live_",
    "sk_test_",
    "pk_test_",
    "STRIPE_SECRET_KEY",
    "STRIPE_PUBLISHABLE_KEY",
    # ---- GitHub ----
    "github_token",
    "github_personal_access_token",
    "github_oauth_token",
    "github_webhook_secret",
    "ghp_",
    "gho_",
    "ghu_",
    "ghs_",
    "ghr_",  # GitHub PAT
    "GITHUB_TOKEN",
    "GITHUB_ACCESS_TOKEN",
    "GITHUB_SECRET",
    "GITHUB_OAUTH_TOKEN",
    # ---- GitLab ----
    "gitlab_token",
    "gitlab_private_token",
    "gitlab_oauth_token",
    "gitlab_webhook_secret",
    "GITLAB_TOKEN",
    "GITLAB_PRIVATE_TOKEN",
    "GITLAB_OAUTH_TOKEN",
    # ---- Slack ----
    "slack_token",
    "slack-token",
    "slacktoken",
    "slack_bot_token",
    "slack_webhook_url",
    "slack_oauth_token",
    "xox[apbors]-",  # Slack tokens
    "SLACK_TOKEN",
    "SLACK_BOT_TOKEN",
    "SLACK_WEBHOOK_URL",
    "SLACK_OAUTH_TOKEN",
    # ---- OpenAI и AI-services ----
    "openai_api_key",
    "openai_secret_key",
    "anthropic_api_key",
    "cohere_api_key",
    "elevenlabs_api_key",
    "huggingface_api_key",
    "replicate_api_key",
    "stability_api_key",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "COHERE_API_KEY",
    "ELEVENLABS_API_KEY",
    # ---- Twilio, SendGrid, Mailgun и др. ----
    "twilio_account_sid",
    "twilio_auth_token",
    "sendgrid_api_key",
    "mailgun_api_key",
    "mailgun_domain",
    "mailchimp_api_key",
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "SENDGRID_API_KEY",
    "MAILGUN_API_KEY",
    # ---- Docker, Kubernetes ----
    "dockerhub_username",
    "dockerhub_password",
    "dockerhub_token",
    "registry_username",
    "registry_password",
    "kubeconfig",
    "kubernetes_token",
    "kubernetes_cert",
    "DOCKERHUB_USERNAME",
    "DOCKERHUB_PASSWORD",
    "DOCKERHUB_TOKEN",
    "KUBECONFIG",
    # ---- CI/CD (Jenkins, Travis, CircleCI, GitLab CI) ----
    "jenkins_user",
    "jenkins_password",
    "jenkins_token",
    "travis_token",
    "circleci_token",
    "CI_JOB_TOKEN",
    "CI_PROJECT_TOKEN",
    "CI_DEPLOY_USER",
    "CI_DEPLOY_PASSWORD",
    "DEPLOY_TOKEN",
    "DEPLOY_KEY",
    # ---- Brokers  ----
    "rabbitmq_default_user",
    "rabbitmq_default_pass",
    "kafka_username",
    "kafka_password",
    "sqs_access_key",
    "sqs_secret_key",
    # ---- Cloud ----
    "s3_access_key",
    "s3_secret_key",
    "s3_bucket_name",
    "gcs_credentials",
    "azure_storage_account",
    "azure_storage_key",
    # ---- JWT и OAuth ----
    "jwt_secret",
    "jwt_private_key",
    "jwt_public_key",
    "oauth2_client_id",
    "oauth2_client_secret",
    "oauth2_redirect_uri",
    "JWT_SECRET",
    "JWT_PRIVATE_KEY",
    "JWT_PUBLIC_KEY",
    "secret",
    "credentials",
    "credential",
    "confidential",
    "private",
    "sensitive",
    "admin_password",
    "root_password",
    "db_password",
    "webhook_secret",
    "hook_secret",
    "deploy_key",
    "deploy_token",
    "service_account_key",
    "service_account_json",
    "oidc_client_secret",
    "oidc_token",
    "tls_private_key",
    "tls_cert",
    "ldap_password",
    "ldap_bind_dn",
    "spr_",
    "rp_",
    "pp_",
    "v1_",
    "v2_",
    "prod_",
    "test_",
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
        self._token_list = token.split(";")
        self._base = "https://api.github.com"
        self._headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "SkyFall-OSINT/1.0",
        }
        self._current_token_index = 0
        self._token = self._token_list[0]
        if self._token:
            self._headers["Authorization"] = f"Bearer {self._token}"

    def _switch_to_next_token(self) -> bool:
        if self._current_token_index + 1 < len(self._token_list):
            self._current_token_index += 1
            self._token = self._token_list[self._current_token_index]
            self._headers["Authorization"] = f"Bearer {self._token}"
            logger.info(
                f"Switch to: {self._current_token_index + 1}/{len(self._token_list)}"
            )
            return True
        else:
            logger.warning("All tokens exhausted")
            return False

    def _handle_rate_limit(
        self, results: list, on_result: Callable | None = None
    ) -> bool:
        if self._switch_to_next_token():
            msg = f"Rate limited. Switching to token {self._current_token_index + 1}"
            results.append(f"\n{error(msg)}")
            if on_result:
                on_result(results[-1])
            return True
        else:
            msg = "Rate limited. All tokens exhausted."
            results.append(f"\n{error(msg)}")
            if on_result:
                on_result(results[-1])
            return False

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
                    if self._handle_rate_limit(results, on_result):
                        continue
                    else:
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
                    entry = f"{bullet(repo)}\n{line(path)}\n{line(url)}"
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

        output = [divider(), title(f"Email search results for {query!r}:")]
        output.extend(results)
        output.append(end_of("email search"))
        output.append(divider())
        return "\n".join(output)

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

            max_retries = len(self._token_list) if self._token_list else 1
            for attempt in range(max_retries):
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
                            + error(
                                "Bad credentials. Check your GitHub token in settings."
                            )
                        )
                        if on_result:
                            on_result(results[-1])
                        break

                    if resp.status_code == 403:
                        if self._switch_to_next_token():
                            logger.info(
                                f"Rate limited on pattern '{pattern}', retrying with"
                                "next token"
                            )
                            continue
                        else:
                            results.append(
                                f"\n{error('Rate limited. All tokens exhausted.')}"
                            )
                            if on_result:
                                on_result(results[-1])
                            break

                    if resp.status_code != 200:
                        break

                    data = resp.json()
                    items = data.get("items", [])
                    if not items:
                        break

                    results.append(f"\n{section(pattern)}")
                    if on_result:
                        on_result(f"\n{section(pattern)}")

                    for item in items[:3]:
                        repo = item["repository"]["full_name"]
                        path = item["path"]
                        url = item["html_url"]
                        entry = f"{bullet(repo)}\n{line(path)}\n{line(url)}"
                        results.append(entry)
                        if on_result:
                            on_result(entry)
                    break

                except httpx.RequestError:
                    continue

        if not results:
            return "No secrets found."

        output = [divider(), title(f"Secret scan results for {query!r}:")]
        output.extend(results)
        output.append(end_of("secret scan"))
        output.append(divider())
        return "\n".join(output)

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
                            f"{bullet(sha)}\n"
                            f"{line(f'Date: {date}')}\n"
                            f"{line(f'Author: {name} <{email}>')}\n"
                            f"{line(f'Message: {msg}')}\n"
                            f"{line(f'Repo: {q}')}\n"
                            f"{line(url)}"
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
                            f"{bullet(sha)}\n"
                            f"{line(f'Date: {date}')}\n"
                            f"{line(f'Author: {name} <{email}>')}\n"
                            f"{line(f'Message: {msg}')}\n"
                            f"{line(f'Repo: {repo}')}\n"
                            f"{line(url)}"
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

        output = [divider(), title(f"Commit search results for {query!r}:")]
        output.extend(results)
        output.append(end_of("commit search"))
        output.append(divider())
        return "\n".join(output)

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
                        f"{bullet(full_name)} {lang} | {stars}★ {forks}⑃\n"
                        f"{line(desc)}\n"
                        f"{line(url)}"
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

        output = [divider(), title(f"Repository search results for {query!r}:")]
        output.extend(results)
        output.append(end_of("repo search"))
        output.append(divider())
        return "\n".join(output)

    async def search_user(
        self,
        username: str,
        on_result: Callable | None = None,
    ) -> str:
        lines = []

        lines.append(divider())
        if on_result:
            on_result(divider())
        lines.append(title(f"GitHub User: {username}"))
        if on_result:
            on_result(title(f"GitHub User: {username}"))

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

        lines.append(end_of("user search"))
        if on_result:
            on_result(end_of("user search"))
        lines.append(divider())
        if on_result:
            on_result(divider())
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
                    if self._switch_to_next_token():
                        results.append(
                            f"\n{error('Rate limited. Switching to new token')}"
                        )
                        if on_result:
                            on_result(results[-1])
                        continue
                    else:
                        results.append(
                            f"\n{error('Rate limited. All tokens exhausted.')}"
                        )
                        if on_result:
                            on_result(results[-1])
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
                        entry = f"{bullet(repo)}\n{line(path)}\n{line(url)}"
                    elif dork_type == "commits":
                        author = item.get("commit", {}).get("author", {})
                        email = author.get("email", "N/A")
                        name = author.get("name", "N/A")
                        msg = item.get("commit", {}).get("message", "").split("\n")[0]
                        repo = item["repository"]["full_name"]
                        sha = item["sha"][:8]
                        url = item["html_url"]
                        entry = (
                            f"{bullet(sha)}\n"
                            f"{line(f'Author: {name} <{email}>')}\n"
                            f"{line(f'Message: {msg}')}\n"
                            f"{line(f'Repo: {repo}')}\n"
                            f"{line(url)}"
                        )
                    elif dork_type == "issues":
                        repo = item["repository"]["full_name"]
                        issue_title = item["title"]
                        state = item["state"]
                        url = item["html_url"]
                        entry = (
                            f"{bullet(repo)}\n"
                            f"{line(f'[{state}] {issue_title}')}\n"
                            f"{line(url)}"
                        )
                    elif dork_type == "repositories":
                        full_name = item["full_name"]
                        desc = item.get("description") or "No description"
                        stars = item["stargazers_count"]
                        lang = item.get("language") or "N/A"
                        url = item["html_url"]
                        entry = (
                            f"{bullet(full_name)} {lang} | {stars}★\n"
                            f"{line(desc)}\n"
                            f"{line(url)}"
                        )
                    elif dork_type == "users":
                        login = item["login"]
                        uid = item["id"]
                        url = item["html_url"]
                        entry = (
                            f"{bullet(login)}\n"
                            f"{line(f'(id: {uid})')}\n"
                            f"{line(url)}"
                        )
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

        output = [divider(), title(f"Dork results for {query!r} ({dork_type}):")]
        output.extend(results)
        output.append(end_of("dork search"))
        output.append(divider())
        return "\n".join(output)
