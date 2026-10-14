from collections.abc import Callable

import httpx
from loguru import logger

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
    # ---- OpenAI and AI-services ----
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
    # ---- Twilio, SendGrid, Mailgun and others ----
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
    # ---- JWT and OAuth ----
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

    def _handle_rate_limit(self, errors: list) -> bool:
        if self._switch_to_next_token():
            errors.append(
                f"Rate limited. Switching to token {self._current_token_index + 1}"
            )
            return True
        errors.append("Rate limited. All tokens exhausted.")
        return False

    def _rate_limit_remaining(self, resp: httpx.Response) -> tuple[int, int]:
        remaining = int(resp.headers.get("X-RateLimit-Remaining", 0))
        limit = int(resp.headers.get("X-RateLimit-Limit", 60))
        return remaining, limit

    async def search_emails(
        self,
        query: str,
        on_progress: Callable | None = None,
    ) -> dict:
        results = []
        errors = []
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
                    if self._handle_rate_limit(errors):
                        continue
                    break

                if resp.status_code != 200:
                    errors.append(f"API error {resp.status_code}")
                    break

                payload = resp.json()
                items = payload.get("items", [])
                if not items:
                    break

                remaining, limit = self._rate_limit_remaining(resp)
                if on_progress:
                    on_progress(page, remaining, limit)

                for item in items:
                    results.append(
                        {
                            "repo": item["repository"]["full_name"],
                            "path": item["path"],
                            "url": item["html_url"],
                        }
                    )

                page += 1
                if payload.get("total_count", 0) < page * per_page:
                    break

            except httpx.RequestError as e:
                errors.append(f"Request failed: {e}")
                break

        data: dict = {"query": query}
        if results:
            data["results"] = results
        if errors:
            data["errors"] = errors
        if not results and not errors:
            data["message"] = "No email results found."
        return data

    async def search_secrets(
        self,
        query: str,
        pattern_filter: list[str] | None = None,
        on_progress: Callable | None = None,
    ) -> dict:
        matches = []
        errors = []
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
                        errors.append(
                            "Bad credentials. Check your GitHub token in settings."
                        )
                        break

                    if resp.status_code == 403:
                        if self._switch_to_next_token():
                            logger.info(
                                f"Rate limited on pattern '{pattern}', retrying with"
                                "next token"
                            )
                            continue
                        errors.append("Rate limited. All tokens exhausted.")
                        break

                    if resp.status_code != 200:
                        break

                    payload = resp.json()
                    items = payload.get("items", [])
                    if not items:
                        break

                    entries = [
                        {
                            "repo": item["repository"]["full_name"],
                            "path": item["path"],
                            "url": item["html_url"],
                        }
                        for item in items[:3]
                    ]
                    matches.append({"pattern": pattern, "items": entries})
                    break

                except httpx.RequestError:
                    continue

        data: dict = {"query": query}
        if matches:
            data["matches"] = matches
        if errors:
            data["errors"] = errors
        if not matches and not errors:
            data["message"] = "No secrets found."
        return data

    @staticmethod
    def _commit_entry(item, repo_name=None):
        author = item.get("commit", {}).get("author", {})
        return {
            "sha": item["sha"][:8],
            "date": author.get("date", "").split("T")[0],
            "author": author.get("name", "N/A"),
            "email": author.get("email", "N/A"),
            "message": item.get("commit", {}).get("message", "").split("\n")[0],
            "repo": repo_name or item["repository"]["full_name"],
            "url": item["html_url"],
        }

    async def search_commits(
        self,
        query: str,
        on_progress: Callable | None = None,
    ) -> dict:
        results = []
        errors = []
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
                        errors.append("Rate limited.")
                        break
                    if resp.status_code == 404:
                        errors.append(f"Repo {q!r} not found.")
                        break
                    if resp.status_code != 200:
                        errors.append(f"API error {resp.status_code}")
                        break

                    items = resp.json()
                    if not items:
                        break

                    if on_progress:
                        on_progress(page, 0, 0)

                    for item in items:
                        results.append(self._commit_entry(item, repo_name=q))

                    page += 1
                    params["page"] = page

                    link = resp.headers.get("Link", "")
                    if 'rel="next"' not in link:
                        break

                except httpx.RequestError as e:
                    errors.append(f"Request failed: {e}")
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
                        errors.append("Rate limited.")
                        break
                    if resp.status_code != 200:
                        errors.append(f"API error {resp.status_code}")
                        break

                    payload = resp.json()
                    items = payload.get("items", [])
                    if not items:
                        break

                    remaining, limit = self._rate_limit_remaining(resp)
                    if on_progress:
                        on_progress(page, remaining, limit)

                    for item in items:
                        results.append(self._commit_entry(item))

                    page += 1
                    if payload.get("total_count", 0) < page * per_page:
                        break

                except httpx.RequestError as e:
                    errors.append(f"Request failed: {e}")
                    break

        data: dict = {"query": query}
        if results:
            data["commits"] = results
        if errors:
            data["errors"] = errors
        if not results and not errors:
            data["message"] = "No commits found."
        return data

    @staticmethod
    def _repo_entry(item):
        return {
            "full_name": item["full_name"],
            "description": item.get("description") or "No description",
            "stars": item["stargazers_count"],
            "forks": item["forks_count"],
            "language": item.get("language") or "N/A",
            "url": item["html_url"],
        }

    async def search_repos(
        self,
        query: str,
        on_progress: Callable | None = None,
    ) -> dict:
        results = []
        errors = []
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
                    errors.append("Rate limited.")
                    break
                if resp.status_code != 200:
                    errors.append(f"API error {resp.status_code}")
                    break

                payload = resp.json()
                items = payload.get("items", [])
                if not items:
                    break

                remaining, limit = self._rate_limit_remaining(resp)
                if on_progress:
                    on_progress(page, remaining, limit)

                for item in items:
                    results.append(self._repo_entry(item))

                page += 1
                if payload.get("total_count", 0) < page * per_page:
                    break

            except httpx.RequestError as e:
                errors.append(f"Request failed: {e}")
                break

        data: dict = {"query": query}
        if results:
            data["repositories"] = results
        if errors:
            data["errors"] = errors
        if not results and not errors:
            data["message"] = "No repositories found."
        return data

    async def search_user(self, username: str) -> dict:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"{self._base}/users/{username}",
                    headers=self._headers,
                )

                if resp.status_code == 403:
                    return {"username": username, "error": "Rate limited."}
                if resp.status_code == 404:
                    return {
                        "username": username,
                        "error": f"User '{username}' not found.",
                    }
                if resp.status_code != 200:
                    return {
                        "username": username,
                        "error": f"API error {resp.status_code}",
                    }

                payload = resp.json()
                profile = {}
                fields = [
                    ("login", "login"),
                    ("name", "name"),
                    ("company", "company"),
                    ("blog", "blog"),
                    ("email", "email"),
                    ("bio", "bio"),
                    ("twitter", "twitter_username"),
                    ("location", "location"),
                    ("public_repos", "public_repos"),
                    ("followers", "followers"),
                    ("following", "following"),
                    ("created", "created_at"),
                    ("type", "type"),
                    ("hireable", "hireable"),
                ]
                for label, key in fields:
                    val = payload.get(key)
                    if val is not None and val != "":
                        profile[label] = val

                data: dict = {"username": username, "profile": profile}

                resp2 = await client.get(
                    f"{self._base}/users/{username}/repos",
                    params={"per_page": 30, "sort": "updated"},
                    headers=self._headers,
                )
                if resp2.status_code == 200:
                    repos = resp2.json()
                    if repos:
                        data["repos"] = [
                            {
                                "full_name": r["full_name"],
                                "language": r.get("language") or "N/A",
                            }
                            for r in repos[:15]
                        ]

                return data

        except httpx.RequestError as e:
            return {"username": username, "error": f"Request failed: {e}"}

    @staticmethod
    def _dork_entry(item, dork_type):
        if dork_type == "code":
            return {
                "repo": item["repository"]["full_name"],
                "path": item["path"],
                "url": item["html_url"],
            }
        if dork_type == "commits":
            author = item.get("commit", {}).get("author", {})
            return {
                "sha": item["sha"][:8],
                "author": author.get("name", "N/A"),
                "email": author.get("email", "N/A"),
                "message": item.get("commit", {}).get("message", "").split("\n")[0],
                "repo": item["repository"]["full_name"],
                "url": item["html_url"],
            }
        if dork_type == "issues":
            return {
                "repo": item["repository"]["full_name"],
                "state": item["state"],
                "title": item["title"],
                "url": item["html_url"],
            }
        if dork_type == "repositories":
            return {
                "full_name": item["full_name"],
                "language": item.get("language") or "N/A",
                "stars": item["stargazers_count"],
                "description": item.get("description") or "No description",
                "url": item["html_url"],
            }
        if dork_type == "users":
            return {
                "login": item["login"],
                "id": item["id"],
                "url": item["html_url"],
            }
        return {"raw": str(item)}

    async def search_dork(
        self,
        query: str,
        dork_type: str = "code",
        on_progress: Callable | None = None,
    ) -> dict:
        results = []
        errors = []
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
                        errors.append("Rate limited. Switching to new token")
                        continue
                    errors.append("Rate limited. All tokens exhausted.")
                    break

                if resp.status_code != 200:
                    errors.append(f"API error {resp.status_code}")
                    break

                payload = resp.json()
                items = payload.get("items", [])
                if not items:
                    break

                remaining, limit = self._rate_limit_remaining(resp)
                if on_progress:
                    on_progress(page, remaining, limit)

                for item in items:
                    results.append(self._dork_entry(item, dork_type))

                page += 1
                total = payload.get("total_count", 0)
                if total < page * per_page:
                    break

            except httpx.RequestError as e:
                errors.append(f"Request failed: {e}")
                break

        data: dict = {"query": query, "dork_type": dork_type}
        if results:
            data["results"] = results
        if errors:
            data["errors"] = errors
        if not results and not errors:
            data["message"] = "No results found."
        return data
