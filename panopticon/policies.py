from abc import ABC, abstractmethod
from typing import List, Dict, Tuple
from .sentinel import Sentinel


class BasePolicy(ABC):
    @abstractmethod
    def evaluate(self, telemetry_stream: List[Dict]) -> Tuple[bool, str, str]:
        pass


import difflib


class AntiLoopPolicy(BasePolicy):
    def __init__(self, window: int = 3, threshold: float = 0.85):
        self.window = window
        self.threshold = threshold

    def evaluate(self, telemetry_stream: List[Dict]) -> Tuple[bool, str, str]:
        if len(telemetry_stream) < self.window:
            return False, "", ""

        recent = [
            entry.get("thought", "").strip()
            for entry in telemetry_stream[-self.window :]
        ]
        if not recent[0]:
            return False, "", ""

        # Flaw 3 Fix: Fuzzy match chunks (≥85% similar) to ignore timestamps/spinners
        ratios = [difflib.SequenceMatcher(None, recent[0], t).ratio() for t in recent]

        if all(r >= self.threshold for r in ratios):
            return (
                True,
                "Heuristic: Fuzzy repetition loop detected",
                "[SYSTEM OVERRIDE] You are repeating the exact same actions. Try a different strategy.",
            )
        return False, "", ""


class BlacklistPolicy(BasePolicy):
    def __init__(self, forbidden_patterns: List[str]):
        self.forbidden_patterns = forbidden_patterns

    def evaluate(self, telemetry_stream: List[Dict]) -> Tuple[bool, str, str]:
        if not telemetry_stream:
            return False, "", ""
        latest = telemetry_stream[-1].get("thought", "").lower()
        for pattern in self.forbidden_patterns:
            if pattern.lower() in latest:
                return (
                    True,
                    f"Blacklisted pattern detected: '{pattern}'",
                    f"[SYSTEM OVERRIDE] You triggered a forbidden action ({pattern}). Reverse course immediately.",
                )
        return False, "", ""


class AdversarialLogicCheck(BasePolicy):
    def __init__(self, target_agent: str = "claude"):
        self.sentinel = Sentinel(target_agent=target_agent)

    def evaluate(self, telemetry_stream: List[Dict]) -> Tuple[bool, str, str]:
        if len(telemetry_stream) >= 2:
            return self.sentinel.evaluate_trajectory(telemetry_stream)
        return False, "", ""
