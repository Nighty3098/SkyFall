def title(text: str) -> str:
    return f"[+] {text}"


def section(name: str) -> str:
    return f"  --- {name} ---"


def end_of(action: str) -> str:
    return f"  ─── End of {action} ───"


def kv(key: str, val: object) -> str:
    return f"  {key}: {val}"


def info(msg: str) -> str:
    return f"  [i] {msg}"


def error(msg: str) -> str:
    return f"  [!] {msg}"


def divider(char: str = "═", length: int = 47) -> str:
    return char * length


def bullet(text: str) -> str:
    return f"  - {text}"


def line(text: str) -> str:
    return f"    {text}"
