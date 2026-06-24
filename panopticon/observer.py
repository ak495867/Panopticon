import json
import os
from typing import List, Dict, Callable
from .policies import BasePolicy


class InterventionException(Exception):
    def __init__(self, message: str, course_correction: str):
        super().__init__(message)
        self.course_correction = course_correction


class PanopticonObserver:
    def __init__(
        self,
        policies: List[BasePolicy] = None,
        telemetry_file: str = "panopticon_telemetry.jsonl",
    ):
        self.policies = policies or []
        self.telemetry_stream = []
        self.telemetry_file = telemetry_file

        if os.path.exists(self.telemetry_file):
            os.remove(self.telemetry_file)

    def _broadcast(self, event_type: str, data: Dict):
        """Writes to a JSONL file so the Pantheon OS Dashboard can tail it in real-time."""
        payload = {"event": event_type, **data}
        with open(self.telemetry_file, "a") as f:
            f.write(json.dumps(payload) + "\n")

    def log_action(self, agent_name: str, thought: str, action: str, tokens_used: int):
        entry = {
            "agent": agent_name,
            "thought": thought,
            "action": action,
            "tokens": tokens_used,
        }
        # Flaw 2 Fix: Bounded memory to prevent leaks
        self.telemetry_stream.append(entry)
        if len(self.telemetry_stream) > 20:
            self.telemetry_stream.pop(0)
        self._broadcast("step", entry)
        self._evaluate_state(agent_name)

    def _evaluate_state(self, agent_name: str):
        for policy in self.policies:
            is_violating, reason, correction = policy.evaluate(self.telemetry_stream)
            if is_violating:
                self._broadcast(
                    "guillotine",
                    {"agent": agent_name, "reason": reason, "correction": correction},
                )
                self._trigger_guillotine(agent_name, reason, correction)

    def _trigger_guillotine(self, agent_name: str, reason: str, correction: str):
        raise InterventionException(message=reason, course_correction=correction)

    def watch(self, agent_name: str):
        def decorator(func: Callable):
            def wrapper(*args, **kwargs):
                self._broadcast("start", {"agent": agent_name})
                try:
                    return func(*args, **kwargs)
                except InterventionException as e:
                    self._broadcast(
                        "interrupt",
                        {"agent": agent_name, "correction": e.course_correction},
                    )
                    return {"status": "interrupted", "correction": e.course_correction}

            return wrapper

        return decorator
