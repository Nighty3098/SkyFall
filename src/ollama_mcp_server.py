"""
Standalone MCP server for SkyFall OSINT report generation via Ollama.

Run directly:  python -m src.ollama_mcp_server
Via app:       spawned as subprocess with stdio transport (MCP protocol)
"""

import json
import logging
from typing import Any

import httpx
from loguru import logger
from mcp.server.fastmcp import FastMCP


class _LoguruInterceptor(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        level = logger.level(record.levelname).name if record.levelname else "INFO"
        logger.opt(depth=6, exception=record.exc_info).log(level, record.getMessage())


logging.basicConfig(handlers=[_LoguruInterceptor()], level=0, force=True)

OLLAMA_BASE = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen3.6:35b-a3b"

_current_model = DEFAULT_MODEL

mcp = FastMCP(
    "SkyFall OSINT Reporter",
    instructions="MCP server for generating OSINT reports via local Ollama",
)


def _ollama_request(method: str, path: str, **kwargs) -> dict[str, Any]:
    with httpx.Client(base_url=OLLAMA_BASE, timeout=120) as client:
        resp = client.request(method, path, **kwargs)
        resp.raise_for_status()
        return resp.json()


def _ollama_generate(prompt: str, model: str | None = None) -> str:
    model = model or _current_model
    full_text = ""
    with httpx.Client(base_url=OLLAMA_BASE, timeout=300) as client:
        with client.stream(
            "POST",
            "/api/generate",
            json={"model": model, "prompt": prompt, "stream": True},
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        full_text += chunk.get("response", "")
                    except json.JSONDecodeError:
                        pass
    return full_text


@mcp.tool()
def get_ollama_model() -> str:
    """Get the currently configured Ollama model name."""
    return _current_model


@mcp.tool()
def set_ollama_model(model_name: str) -> str:
    """Set the Ollama model to use for report generation."""
    global _current_model
    _current_model = model_name
    return f"Model set to: {_current_model}"


@mcp.tool()
def list_ollama_models() -> str:
    """List all available models in your local Ollama."""
    try:
        data = _ollama_request("GET", "/api/tags")
        models = [m["name"] for m in data.get("models", [])]
        if not models:
            return "No models found in Ollama"
        return "Available models:\n" + "\n".join(f"  - {m}" for m in models)
    except httpx.HTTPError as e:
        return f"Error connecting to Ollama: {e}"


@mcp.tool()
def generate_osint_report(app_data: str) -> str:
    """
    Generate an OSINT report from the collected application data.

    Args:
        app_data: JSON string containing all collected OSINT data from the application
    """
    try:
        data = json.loads(app_data)
    except json.JSONDecodeError:
        data = {"raw": app_data}

    prompt = _build_prompt(data)
    return _ollama_generate(prompt)


def _build_prompt(data: dict) -> str:
    sections = []
    for key, value in data.items():
        if value:
            if isinstance(value, (dict, list)):
                sections.append(
                    f"### {key}\n{json.dumps(value, indent=2, ensure_ascii=False)}"
                )
            else:
                sections.append(f"### {key}\n{str(value)}")
    data_str = "\n\n".join(sections)

    prompt = (
        "РОЛЬ:\n"
        "Ты — независимый аналитик по OSINT (разведка по открытым источникам) "
        "с 10-летним опытом. Ты работаешь строго по фактам, разделяешь "
        "подтвержденные данные и гипотезы. Ты не делаешь моральных оценок, "
        "только фиксируешь связи и временные метки.\n\n"
        "ЗАДАЧА:\n"
        "Провести многоуровневый анализ по входным данным ниже. "
        "Сформировать отчет по структуре ниже. Если данных по какому-то "
        "пункту нет — пиши «Информация отсутствует», не придумывай.\n\n"
        "СТРУКТУРА ОТЧЕТА:\n\n"
        "1. ИСХОДНЫЕ ДАННЫЕ И ИХ ВЕРИФИКАЦИЯ\n"
        "   - Что именно дано на вход (тип объекта)\n"
        "   - Первичный анализ: уникальный, сгенерированный или реальный\n\n"
        "2. ЦИФРОВОЙ СЛЕД (Платформы и аккаунты)\n"
        "   - Социальные сети: перечисли все найденные профили, укажи активность\n"
        "   - Профессиональные и медиа-площадки, если применимо\n"
        "   - Для каждого аккаунта укажи: Совпадение (высокое/среднее/низкое) "
        "и ссылку\n\n"
        "3. ИНФРАСТРУКТУРА (Если применимо)\n"
        "   - Домены, связанные с email/ником\n"
        "   - Субдомены и IP\n"
        "   - Связанные email-адреса, утечки баз данных\n\n"
        "4. ВРЕМЕННАЯ ЛИНИЯ (Таймлайн)\n"
        "   - Ключевые даты активности\n"
        "   - Смена аватаров, юзернеймов\n\n"
        "5. ГЕОЛОКАЦИЯ И РЕАЛЬНЫЙ МИР\n"
        "   - IP-адреса, местоположение по EXIF\n"
        "   - Упоминания городов, мест работы, учебных заведений\n"
        "   - Связи с другими людьми\n\n"
        "6. ОЦЕНКА УЯЗВИМОСТЕЙ И РИСКОВ\n"
        "   - Насколько легко найти человека в офлайн-мире (шкала 1-10)\n"
        "   - Какие данные защищены, а какие в открытом доступе\n"
        "   - Рекомендации по закрытию пробелов\n\n"
        "7. ВЫВОДЫ И ДАЛЬНЕЙШИЕ ШАГИ\n"
        "   - Сборка пазла: гипотеза о субъекте\n"
        "   - 3 следующих действия для углубления поиска\n\n"
        "ПРАВИЛА ФОРМАТИРОВАНИЯ:\n"
        "- Используй Markdown (заголовки #, списки -, жирный шрифт)\n"
        "- В конце отчета поставь «Процент уверенности» по каждому блоку "
        "(0-100%)\n"
        "- Веди отсчет времени в UTC\n\n"
        "ОГРАНИЧЕНИЯ:\n"
        "- Запрещено писать субъективные оскорбления\n"
        "- Если данных критически мало (< 3 символов), напиши: "
        "«Недостаточно данных для генерации отчета» и остановись\n\n"
        f"---\n\nСОБРАННЫЕ ДАННЫЕ:\n{data_str}\n\n"
        "Сгенерируй ТОЛЬКО markdown отчет. Без лишних комментариев."
    )

    return prompt


if __name__ == "__main__":
    mcp.run(transport="stdio")
