import re
from urllib.parse import urlparse


def extract_links(text: str) -> list[tuple[str, str]]:
    """Extract URLs and Telegram mentions from text with surrounding context.

    Supports HTTP(S) URLs, t.me links, telegram.me links, and @usernames.

    Args:
        text (str): Text to extract URLs from.

    Returns:
        List[Tuple[str, str]]: List of (url, context) tuples where context
                               is the surrounding text (up to 50 chars before/after).
    """
    if not text:
        return []

    url_pattern = re.compile(
        r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+|"
        r"t\.me/[a-zA-Z0-9_]+|"
        r"telegram\.me/[a-zA-Z0-9_]+|"
        r"@[a-zA-Z1-9_]+"
    )

    links = []
    for match in url_pattern.finditer(text):
        url = match.group()
        if url.startswith("t.me/"):
            url = f"https://{url}"
        elif url.startswith("telegram.me/"):
            url = f"https://{url}"
        elif url.startswith("@"):
            url = f"https://t.me/{url[1:]}"

        start = max(0, match.start() - 50)
        end = min(len(text), match.end() + 50)
        context = text[start:end]

        links.append((url, context))

    return links


def get_link_type(url: str) -> str:
    """Determine the type/category of a URL.

    Args:
        url (str): URL to analyze.

    Returns:
        str: Link type - 'telegram' for Telegram links, scheme name (http, https, etc.)
             for other URLs, or 'unknown' if not determinable.
    """
    parsed = urlparse(url)
    if "t.me" in parsed.netloc or "telegram.me" in parsed.netloc:
        return "telegram"
    elif parsed.scheme:
        return parsed.scheme
    return "unknown"
