"""観測日誌の解答を、欄ごとの個体集合で採点する。"""

from collections.abc import Sequence
from typing import TypedDict
from unicodedata import normalize


class GradingResult(TypedDict):
    correct: float
    field_accuracy: float
    format_error: float
    field_matches: list[bool]


def _parse_field(field: str, symbols: set[str]) -> set[str] | None:
    field = field.strip().removesuffix("。").rstrip()
    if field == "なし":
        return set()
    # 読点などの区切りは、記号の間に限って許容する。
    if not field or field[0] not in symbols or field[-1] not in symbols:
        return None
    chars = [char for char in field if not char.isspace() and char not in "、,・"]
    parsed = set(chars)
    if not parsed <= symbols or len(parsed) != len(chars):
        return None
    return parsed


def find_answer_line(lines: Sequence[str]) -> tuple[int, str] | None:
    """Return the index and normalized text of the last recognized answer line."""
    for index in range(len(lines) - 1, -1, -1):
        raw = lines[index]
        line = normalize("NFKC", raw).strip()
        while marker := next((marker for marker in ("**", "*", "__", "`")
                              if len(line) > 2 * len(marker)
                              and line.startswith(marker) and line.endswith(marker)), None):
            line = line[len(marker):-len(marker)].strip()
        if line.startswith("解答:"):
            return index, line
    return None


def score_answer(
    reply: str | None,
    *,
    field_count: int,
    symbols: Sequence[str],
    gold: Sequence[Sequence[str]],
) -> GradingResult | None:
    """最後に現れる解答行を採点する。応答が無ければ None を返す。"""
    if field_count <= 0:
        raise ValueError("field_count must be positive")
    if len(gold) != field_count:
        raise ValueError("gold length must match field_count")
    if reply is None:
        return None

    answer = find_answer_line(reply.splitlines())
    fields = answer[1].removeprefix("解答:").split("/") if answer is not None else []

    if len(fields) == field_count:
        allowed = set(symbols)
        parsed = [_parse_field(field, allowed) for field in fields]
        matches = [actual == set(expected) for actual, expected in zip(parsed, gold, strict=True)]
        format_error = any(field is None for field in parsed)
    else:
        matches = [False] * field_count
        format_error = True

    return {
        "correct": float(not format_error and all(matches)),
        "field_accuracy": sum(matches) / field_count,
        "format_error": float(format_error),
        "field_matches": matches,
    }
