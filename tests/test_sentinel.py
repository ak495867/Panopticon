import json
from unittest.mock import patch
from panopticon.sentinel import Sentinel


def test_sentinel_json_extraction():
    sentinel = Sentinel("claude")

    # Mock an LLM outputting heavy conversational fluff around the actual JSON payload
    fluff_response = """Based on the execution trace, the agent is stuck in a loop.
    Here is the structured evaluation:
    {
        "is_failing": true,
        "reason": "Agent is stuck in git rebase loop.",
        "correction_prompt": "Run git rebase --abort and start over."
    }
    I hope this helps the system recover!"""

    # Mock the API call and the DB to prevent network/disk usage during tests
    with patch.object(sentinel, "_route_to_llm", return_value=fluff_response):
        with patch.object(sentinel.memory, "get_relevant_failures", return_value=[]):
            with patch.object(sentinel.memory, "record_failure") as mock_record:

                stream = [{"thought": "git step 1"}] * 3
                is_failing, reason, correction = sentinel.evaluate_trajectory(stream)

                # Verify the regex cleanly extracted the JSON out of the conversational fluff
                assert is_failing == True
                assert reason == "Agent is stuck in git rebase loop."
                assert correction == "Run git rebase --abort and start over."

                # Verify the failure was recorded in memory
                mock_record.assert_called_once_with(reason, correction)
