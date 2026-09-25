"""Per-language expansion data: alphabets and question prefixes."""

QUESTION_PREFIXES: dict[str, list[str]] = {
    "ru": ["как", "почему", "что такое", "зачем", "где", "когда", "сколько стоит", "какой лучше"],
    "en": ["how to", "why", "what is", "where", "when", "how much", "best", "vs"],
    "es": ["como", "por que", "que es", "donde", "cuando", "cuanto cuesta", "mejor"],
    "pt": ["como", "por que", "o que e", "onde", "quando", "quanto custa", "melhor"],
    "de": ["wie", "warum", "was ist", "wo", "wann", "wie viel kostet", "beste"],
    "fr": ["comment", "pourquoi", "qu'est-ce que", "où", "quand", "combien coûte", "meilleur"],
    "it": ["come", "perché", "cos'è", "dove", "quando", "quanto costa", "migliore"],
}

_LATIN = list("abcdefghijklmnopqrstuvwxyz")
ALPHABETS: dict[str, list[str]] = {
    "ru": list("абвгдежзиклмнопрстуфхцчшщэюя"),
    "en": _LATIN,
    "es": _LATIN + ["ñ"],
    "pt": _LATIN,
    "de": _LATIN,
    "fr": _LATIN,
    "it": _LATIN,
}


def alphabet(hl: str) -> list[str]:
    return ALPHABETS.get(hl.split("-")[0], _LATIN)


def question_prefixes(hl: str) -> list[str]:
    return QUESTION_PREFIXES.get(hl.split("-")[0], QUESTION_PREFIXES["en"])


def parse_locale(locale: str) -> tuple[str, str]:
    """'es:mx' -> ('es', 'mx'); 'en' -> ('en', 'en')."""
    hl, _, gl = locale.partition(":")
    return hl, gl or hl
