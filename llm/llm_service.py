"""Shared, opt-in inference entrypoint for L4 and L3 (POC 1).

No client, credentials or network are required to construct LLMService.
Existing legacy decision methods are retained for compatibility.
L2 integration is explicitly deferred.
"""
from dataclasses import dataclass
from typing import Any
import json


@dataclass(frozen=True)
class InferenceResult:
    level: str
    output: dict[str, Any]
    provider: str
    model: str
    request_id: str | None = None


class LLMService:
    ALLOWED_LEVELS = frozenset({"L3", "L4"})

    def __init__(self, backend="stub", model=None, client=None, timeout_s=20.0):
        if backend not in ("stub", "openai"):
            raise ValueError("Unsupported inference backend")
        if timeout_s <= 0:
            raise ValueError("timeout_s must be positive")
        self.backend = backend
        self.model = model
        self.client = client
        self.timeout_s = timeout_s

    def infer(self, level, instructions, context, allowed_decisions):
        """Return validated structured advice; never a motor command.

        Callers are responsible for deciding *when* to ask for advice,
        applying mission/navigation constraints and fail-safe behavior.
        """
        if level not in self.ALLOWED_LEVELS:
            raise ValueError("Only L3/L4 may use shared inference in POC 1")
        if not isinstance(instructions, str) or not instructions.strip():
            raise ValueError("instructions must be non-empty")
        if not isinstance(context, dict):
            raise TypeError("context must be a dictionary")
        decisions = tuple(allowed_decisions)
        if not decisions or any(not isinstance(x, str) or not x for x in decisions):
            raise ValueError("allowed_decisions must contain non-empty strings")
        if any(x in {"MOVE_FORWARD", "MOVE_BACKWARD", "FORWARD_LEFT", "FORWARD_RIGHT"}
               for x in decisions):
            raise ValueError("Motor-level decisions are not allowed")

        if self.backend == "stub":
            return InferenceResult(
                level=level,
                output={"decision": decisions[0], "reason": "Offline stub"},
                provider="stub",
                model="deterministic",
            )

        # Lazy import and client initialization: no side effects unless called.
        if not self.model:
            raise ValueError("OpenAI model must be configured")
        if self.client is None:
            from openai import OpenAI
            self.client = OpenAI(timeout=self.timeout_s)
        response = self.client.responses.create(
            model=self.model,
            instructions=(instructions + "\nReturn one JSON object with "
                          "decision and reason. No other fields."),
            input=json.dumps({"level": level,
                              "allowed_decisions": decisions,
                              "context": context}, default=str),
        )
        try:
            payload = json.loads(response.output_text)
        except (ValueError, TypeError) as exc:
            raise ValueError("Inference returned invalid JSON") from exc
        if (not isinstance(payload, dict)
                or set(payload) != {"decision", "reason"}
                or payload["decision"] not in decisions
                or not isinstance(payload["reason"], str)):
            raise ValueError("Inference output failed schema validation")
        return InferenceResult(level=level, output=payload,
                               provider="openai", model=self.model,
                               request_id=getattr(response, "id", None))

    def plan_objectives(self, intent, approved_objectives, context=None):
        """Return a validated ordering of approved objective IDs.

        GPT may reorder the supplied options but may not add destinations,
        omit any required objective, or issue physical commands.
        """
        if not isinstance(intent, str) or not intent.strip():
            raise ValueError("Mission intent required")
        if not isinstance(approved_objectives, (list, tuple)):
            raise TypeError("approved_objectives must be a sequence")
        options = list(approved_objectives)
        if not options or any(not isinstance(x, dict)
                              or not isinstance(x.get("objective_id"), str)
                              or not x["objective_id"] for x in options):
            raise ValueError("Approved objectives must contain IDs")
        ids = [x["objective_id"] for x in options]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate objective IDs")
        if context is not None and not isinstance(context, dict):
            raise TypeError("context must be a dictionary")
        if self.backend == "stub":
            return InferenceResult(
                level="L4",
                output={"objective_ids": ids, "reason": "Offline approved order"},
                provider="stub", model="deterministic",
            )
        if not self.model:
            raise ValueError("OpenAI model must be configured")
        if self.client is None:
            from openai import OpenAI
            self.client = OpenAI(timeout=self.timeout_s)
        response = self.client.responses.create(
            model=self.model,
            instructions=("You are L4 mission planner. Order ALL supplied "
                          "pre-approved observation objectives according to intent "
                          "and context. Never invent, omit or modify destinations. "
                          "Return JSON with keys objective_ids (a list) and reason (a string)."),
            input=json.dumps({"intent": intent, "approved_objectives": options,
                              "context": context or {}}, default=str),
        )
        try:
            output = json.loads(response.output_text)
        except (ValueError, TypeError) as exc:
            raise ValueError("Invalid plan JSON") from exc
        if (not isinstance(output, dict)
                or set(output) != {"objective_ids", "reason"}
                or not isinstance(output["objective_ids"], list)
                or len(output["objective_ids"]) != len(ids)
                or set(output["objective_ids"]) != set(ids)
                or not isinstance(output["reason"], str)):
            raise ValueError("Plan must order exactly the approved objectives")
        return InferenceResult(
            "L4", output, "openai", self.model,
            getattr(response, "id", None),
        )

    # Legacy methods: keep the existing behavior to avoid a surprise change
    # for previously configured call sites.
    def decide_tactical(self, prompt, image_bytes=None):
        return "MOVE_FORWARD"

    def decide_task_mode(self, prompt):
        return "EXPLORE"

    def decide_mission(self, prompt):
        return "EXPLORE"
