from __future__ import annotations

import jinja2


template_env = jinja2.Environment(
    loader=jinja2.BaseLoader(),
    autoescape=False,
    undefined=jinja2.Undefined,
)

# Кастомные фильтры
template_env.filters["number"] = lambda v: f"{v:,.2f}" if isinstance(v, (int, float)) else str(v)
template_env.filters["round"] = lambda v, n: round(v, n) if isinstance(v, (int, float)) else v


def render_message(template_text: str, data: dict) -> str:
    """
    Рендеринг Markdown-шаблона для Telegram.
    Используется Jinja2 с кастомными фильтрами.
    Доступна переменная data с ответом tool.
    """
    template = template_env.from_string(template_text)
    try:
        return template.render(data=data)
    except Exception as e:
        return f"Ошибка рендеринга шаблона: {e}"
