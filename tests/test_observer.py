import pytest
from panopticon.observer import PanopticonObserver, InterventionException
from panopticon.policies import BasePolicy


class DummyTriggerPolicy(BasePolicy):
    def evaluate(self, stream):
        if stream[-1].get("thought") == "trigger":
            return True, "Triggered by dummy", "Fix the dummy error"
        return False, "", ""


def test_observer_memory_bounds():
    observer = PanopticonObserver()

    # Push 25 entries (limit is 20)
    for i in range(25):
        observer.log_action("agent", f"step {i}", "action", 0)

    # Verify sliding queue bounds
    assert len(observer.telemetry_stream) == 20
    assert observer.telemetry_stream[-1]["thought"] == "step 24"
    assert observer.telemetry_stream[0]["thought"] == "step 5"


def test_observer_policy_intervention():
    observer = PanopticonObserver(policies=[DummyTriggerPolicy()])

    # Normal step
    observer.log_action("agent", "normal step", "action", 0)

    # Trigger step should raise InterventionException
    with pytest.raises(InterventionException) as exc_info:
        observer.log_action("agent", "trigger", "action", 0)

    assert "Triggered by dummy" in str(exc_info.value)
    assert exc_info.value.course_correction == "Fix the dummy error"
