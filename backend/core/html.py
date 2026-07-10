from html import escape


def esc(value: object) -> str:
    return escape("" if value is None else str(value))
