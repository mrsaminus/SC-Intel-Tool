import re


NUMBER_TOKEN_RE = re.compile(r"(?<![\w.])\d[\d, ]*\d(?![\w.])|(?<![\w.])\d(?![\w.])")
GROUPED_NUMBER_RE = re.compile(r"\d{1,3}(?:[ ,]\d{3})+")


def format_grouped_numbers(value):
    text = str(value or "").strip()
    if not text:
        return ""

    return NUMBER_TOKEN_RE.sub(format_number_token, text)


def format_number_token(match):
    token = match.group(0)
    compact = token.replace(",", "").replace(" ", "")
    if not compact.isdigit():
        return token

    if "," in token or " " in token:
        if not GROUPED_NUMBER_RE.fullmatch(token):
            return token
    elif len(compact) <= 3:
        return token

    return f"{int(compact):,}"
