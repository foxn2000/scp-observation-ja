"""SCP 観測日誌ベンチマークの verifiers v1 タスクセット。"""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path

import verifiers.v1 as vf
from pydantic import Field

from scp_observation_ja.grading import GradingResult, score_answer


class ScpObservationData(vf.TaskData):
    prompt: str
    record: dict


class ScpObservationState(vf.State):
    grading_result: GradingResult | None = None


class ScpObservationConfig(vf.TasksetConfig):
    data_path: str = ""
    levels: list[str] | None = None
    origins: list[str] | None = None
    max_tasks: int | None = Field(default=None, ge=0)


class ScpObservationTask(vf.Task[ScpObservationData, ScpObservationState, vf.TaskConfig]):
    def _grade(self, trace: vf.Trace[ScpObservationData, ScpObservationState]) -> GradingResult | None:
        result = trace.state.grading_result
        if result is None and trace.assistant_messages:
            record = self.data.record
            result = score_answer(
                trace.last_reply,
                field_count=len(record["fields"]),
                symbols=record["symbols"],
                gold=record["gold"],
            )
            if result is not None:
                trace.state.grading_result = result
                trace.info["grading"] = result
        return result

    @vf.metric
    async def grading(self, trace: vf.Trace[ScpObservationData, ScpObservationState]) -> dict[str, float]:
        result = self._grade(trace)
        if result is None:
            return {}
        metrics = {"field_accuracy": result["field_accuracy"], "format_error": result["format_error"]}
        for index, matches in enumerate(result["field_matches"], start=1):
            metrics[f"field_{index}_correct"] = float(matches)
        return metrics

    @vf.reward(weight=1.0)
    async def correct(self, trace: vf.Trace[ScpObservationData, ScpObservationState]) -> float:
        result = self._grade(trace)
        if result is None:
            # vf-runner はエラーがあり報酬のないトレースを採点対象から外す。
            raise vf.TaskError("モデルの応答を取得できなかったため採点できません")
        return result["correct"]


class ScpObservationTaskset(vf.Taskset[ScpObservationTask, ScpObservationConfig]):
    def load(self) -> list[ScpObservationTask]:
        cfg = self.config
        if cfg.max_tasks == 0:
            return []
        path = (
            Path(cfg.data_path)
            if cfg.data_path
            else resources.files("scp_observation_ja").joinpath("data", "tasks.jsonl")
        )
        records = []
        with path.open(encoding="utf-8") as lines:
            for line in lines:
                if not line.strip():
                    continue
                record = json.loads(line)
                if record.get("build", {}).get("status") != "accepted":
                    continue
                if cfg.levels is not None and record["level"] not in cfg.levels:
                    continue
                if cfg.origins is not None and record["origin"] not in cfg.origins:
                    continue
                records.append(record)

        records.sort(key=lambda record: record["idx"])
        return [
            ScpObservationTask(
                ScpObservationData(idx=row["idx"], name=row["task_id"], prompt=row["prompt"], record=row),
                cfg.task,
            )
            for row in records[: cfg.max_tasks]
        ]
