import asyncio
import json
from types import SimpleNamespace

import pytest
import verifiers.v1 as vf

from scp_observation_ja import ScpObservationTaskset
from scp_observation_ja.taskset import ScpObservationConfig, ScpObservationState


def load_tasks(**filters):
    return ScpObservationTaskset(ScpObservationConfig(id="scp-observation-ja", **filters)).load()


def test_loads_bundled_tasks_with_only_the_prompt_in_the_user_message():
    tasks = load_tasks()
    assert [task.data.idx for task in tasks] == list(range(100))
    assert len({task.data.name for task in tasks}) == 100
    harness = vf.load_harness(vf.HarnessConfig(id="null"))
    for task in tasks:
        record = task.data.record
        assert record["build"]["status"] == "accepted"
        assert len(record["fields"]) == len(record["gold"])
        assert harness.resolve_prompt(task.data) == (None, record["prompt"])
        assert record["prompt"].startswith("【指示】\n")
        assert record["prompt"].endswith("該当なしは「なし」と書いてください。")


def test_loads_custom_jsonl_and_filters_before_truncating_in_idx_order(tmp_path):
    first, second = [{**task.data.record, "level": "L1", "origin": "jp"} for task in load_tasks(max_tasks=2)]
    later = {**first, "idx": 6, "task_id": "later", "level": "L2", "origin": "translation"}
    earlier = {**second, "idx": 3, "task_id": "earlier", "level": "L2", "origin": "translation"}
    other = {**first, "idx": 9, "task_id": "other", "level": "L2"}
    rows = [later, {"idx": 2, "build": {"status": "rejected"}}, second, earlier, first, other]
    path = tmp_path / "tasks.jsonl"
    path.write_text("\n\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")

    def indices(**filters):
        return [task.data.idx for task in load_tasks(data_path=str(path), **filters)]

    assert indices() == [0, 1, 3, 6, 9]
    assert indices(levels=["L2"]) == [3, 6, 9]
    assert indices(origins=["jp"]) == [0, 1, 9]
    assert indices(levels=["L2"], origins=["translation"], max_tasks=1) == [3]
    assert indices(max_tasks=2) == [0, 1]
    assert indices(levels=["L1"], origins=["translation"]) == []
    assert indices(levels=[]) == []
    assert indices(origins=[]) == []
    assert indices(max_tasks=0) == []


def make_trace(task, reply):
    trace = vf.Trace(
        task=vf.TraceTask(type=type(task).__name__, data=task.data), state=ScpObservationState()
    )
    if reply is not None:
        trace.nodes.append(vf.MessageNode(message=vf.AssistantMessage(content=reply), sampled=True))
    return trace


@pytest.mark.parametrize(
    ("reply", "correct", "format_error", "matches"),
    [
        ("解答: 丙/甲乙丙", 1.0, 0.0, [True, True]),
        ("解答: 丙/甲丙", 0.0, 0.0, [True, False]),
        ("解答: 丙/甲甲", 0.0, 1.0, [True, False]),
        ("", 0.0, 1.0, [False, False]),
    ],
)
def test_registered_reward_metrics_and_persisted_field_matches(tmp_path, reply, correct, format_error, matches):
    path = tmp_path / "grading.jsonl"
    row = {"idx": 0, "task_id": "sample", "prompt": "設問", "build": {"status": "accepted"},
           "fields": [{"key": "f1"}, {"key": "f2"}], "symbols": list("甲乙丙丁"),
           "gold": [["丙"], ["甲", "乙", "丙"]]}
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    task, = load_tasks(data_path=str(path))
    trace = make_trace(task, reply)
    asyncio.run(task.score(trace))

    assert trace.rewards == {"correct": correct}
    assert trace.metrics == {
        "field_accuracy": sum(matches) / len(matches),
        "format_error": format_error,
        "field_1_correct": float(matches[0]),
        "field_2_correct": float(matches[1]),
    }
    assert trace.to_record()["info"]["grading"] == trace.state.grading_result == {
        "correct": correct,
        "field_accuracy": sum(matches) / len(matches),
        "format_error": format_error,
        "field_matches": matches,
    }


def test_no_assistant_message_produces_neither_reward_nor_metrics():
    task = load_tasks()[1]
    trace = make_trace(task, None)
    with pytest.raises(vf.TaskError, match="応答を取得できなかった"):
        asyncio.run(task.score(trace))
    assert trace.rewards == {}
    assert trace.metrics == {}
    assert trace.state.grading_result is None
    assert "grading" not in trace.info


def test_assistant_message_without_a_reply_does_not_record_grading():
    task = load_tasks(max_tasks=1)[0]
    trace = SimpleNamespace(assistant_messages=[object()], last_reply=None, state=ScpObservationState(), info={})
    assert task._grade(trace) is None
    assert trace.state.grading_result is None and "grading" not in trace.info
