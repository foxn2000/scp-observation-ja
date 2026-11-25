import pytest

from scp_observation_ja.grading import score_answer


RECORDS = [
    {"symbols": "甲乙丙丁戊", "gold": ["丙丁", "丁", "丙戊", "戊"]},
    {"symbols": "甲乙丙丁", "gold": ["丙", "甲乙丙"]},
]


@pytest.mark.parametrize("field_count", [0, -1])
def test_field_count_must_be_positive(field_count):
    with pytest.raises(ValueError, match="field_count must be positive"):
        score_answer("解答: なし", field_count=field_count, symbols="甲", gold=[])


@pytest.mark.parametrize("reply", [None, "解答: 甲", "解答: 甲/乙"])
def test_gold_length_must_match_independently_of_the_reply(reply):
    with pytest.raises(ValueError, match="gold length must match field_count"):
        score_answer(reply, field_count=2, symbols="甲乙", gold=[["甲"]])


def score(idx, reply):
    record = RECORDS[idx]
    return score_answer(
        reply, field_count=len(record["gold"]), symbols=record["symbols"], gold=record["gold"]
    )


@pytest.mark.parametrize(
    ("idx", "reply"),
    [
        (0, "解答: 丙丁/丁/丙戊/戊"),
        (0, "解答： 丙丁 / 丁 / 丙戊 / 戊"),
        (0, "解答: 丁丙/丁/戊丙/戊"),
        (0, "解答: 丙、丁/丁/丙・戊/戊"),
        (0, "解答: 丙　丁／丁／丙，戊／戊"),
        (0, "観測が途切れた旧個体は消失する。\r\n\t解答: 丙丁/丁/丙戊/戊\r\n  \r\n"),
        (1, "解答: 丙/甲乙丙"),
        (1, "解答： 丙 / 甲乙丙"),
        (1, "解答: 丙/丙甲乙"),
        (1, "解答: 丙/甲、乙・丙"),
        (1, "解答: 丙／甲, 乙\t丙"),
        (1, "記録時点の認識で判定する。\r　解答: 丙/甲乙丙\r\r"),
        (1, "解答: 丙/甲乙丙\n以上です。"),
        (1, "解答: なし/なし\r\n　**解答： 丙／甲乙丙。**　\r理由は次のとおりです。"),
        (1, "*解答: 丙。 / 甲乙丙。*"),
        (1, "__解答: 丙/甲乙丙__"),
        (1, "`解答: 丙/甲乙丙`"),
    ],
)
def test_accepts_equivalent_answers(idx, reply):
    assert score(idx, reply) == {
        "correct": 1.0,
        "field_accuracy": 1.0,
        "format_error": 0.0,
        "field_matches": [True] * len(RECORDS[idx]["gold"]),
    }


@pytest.mark.parametrize(
    ("idx", "reply", "matches"),
    [
        (0, "解答: 丁/丙丁/丙戊/戊", [False, False, True, True]),
        (0, "解答: 丙/丁/丙戊/戊", [False, True, True, True]),
        (0, "解答: 甲丙丁/丁/丙戊/戊", [False, True, True, True]),
        (0, "解答: なし/丁/丙戊/戊", [False, True, True, True]),
        (0, "解答: 丙丁/丁/丙戊/丁", [True, True, True, False]),
        (1, "解答: 甲乙丙/丙", [False, False]),
        (1, "解答: 丙/甲丙", [True, False]),
        (1, "解答: 丙/甲乙丙丁", [True, False]),
        (1, "解答: なし/甲乙丙", [False, True]),
        (1, "解答: 乙/甲乙丙", [False, True]),
    ],
)
def test_scores_well_formed_wrong_answers(idx, reply, matches):
    assert score(idx, reply) == {
        "correct": 0.0,
        "field_accuracy": sum(matches) / len(matches),
        "format_error": 0.0,
        "field_matches": matches,
    }


@pytest.mark.parametrize(
    ("idx", "expected", "matches"),
    [
        (0, "乙丙丁/丁/乙丙戊/戊", [False, True, False, True]),
        (1, "甲丙/甲乙丙丁", [False, False]),
    ],
)
def test_rejects_mutated_rules(idx, expected, matches):
    assert score(idx, f"解答: {expected}") == {
        "correct": 0.0,
        "field_accuracy": sum(matches) / len(matches),
        "format_error": 0.0,
        "field_matches": matches,
    }


@pytest.mark.parametrize(
    ("reply", "matches"),
    [
        ("丙/甲乙丙", [False, False]),
        ("解答 丙/甲乙丙", [False, False]),
        ("解答: 丙", [False, False]),
        ("解答: 丙/甲乙丙/なし", [False, False]),
        ("解答: /甲乙丙", [False, True]),
        ("解答: 丙/　", [True, False]),
        ("解答: 戊/甲乙丙", [False, True]),
        ("解答: 丙/甲・乙・甲・丙", [True, False]),
        ("解答: 丙なし/甲乙丙", [False, True]),
        ("解答: なし、丙/甲乙丙", [False, True]),
        ("解答: ・/甲乙丙", [False, True]),
        ("解答: 、丙/甲乙丙", [False, True]),
        ("解答: 丙/甲乙丙、", [True, False]),
        ("解答: 丙/甲乙丙\n解答: 丙/甲甲。\n以上です。", [True, False]),
        ("答えは解答: 丙/甲乙丙", [False, False]),
        ("", [False, False]),
    ],
)
def test_rejects_bad_format_and_keeps_other_field_matches(reply, matches):
    assert score(1, reply) == {
        "correct": 0.0,
        "field_accuracy": sum(matches) / len(matches),
        "format_error": 1.0,
        "field_matches": matches,
    }


@pytest.mark.parametrize("reply", ["解答： 丙、甲 ／ なし", "**解答: 甲丙/なし**", "解答: 甲丙/なし。"])
def test_empty_set_is_valid_when_expected(reply):
    assert score_answer(reply, field_count=2, symbols="甲丙", gold=[["甲", "丙"], []]) == {
        "correct": 1.0,
        "field_accuracy": 1.0,
        "format_error": 0.0,
        "field_matches": [True, True],
    }


def test_missing_response_is_ungraded():
    assert score(1, None) is None
