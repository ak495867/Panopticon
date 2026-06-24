import json
import os
from typing import List, Dict, Tuple
from .memory import PersistentMemory


class Sentinel:
    """
    The Universal Meta-Agent.
    Dynamically routes its semantic evaluation to match the API of the agent it is observing.
    """

    def __init__(self, target_agent: str = "claude"):
        self.target_agent = target_agent.lower()
        self.memory = PersistentMemory()

    def evaluate_trajectory(
        self, telemetry_stream: List[Dict]
    ) -> Tuple[bool, str, str]:
        if len(telemetry_stream) < 2:
            return False, "", ""

        recent_chunks = [e.get("thought", "")[:500] for e in telemetry_stream[-3:]]
        context_str = " ".join(recent_chunks)

        # Pull dynamically relevant failures based on current context
        past_failures = self.memory.get_relevant_failures(
            current_context=context_str, limit=3
        )

        prompt = f"""
Execution trace:
{json.dumps(recent_chunks)}

Relevant past failures (Do not repeat these mistakes):
{json.dumps(past_failures)}

Is the agent stuck in a loop, failing logical progress, or repeating a past recorded failure?
Respond ONLY in JSON:
{{"is_failing": true/false, "reason": "why if true", "correction_prompt": "directive prompt to inject to break the loop or correct the logic. empty if not failing"}}
"""
        try:
            result_text = self._route_to_llm(prompt)

            # Flaw 4 Fix: Robust regex JSON extraction ignoring conversational fluff
            import re

            match = re.search(r"\{.*\}", result_text, re.DOTALL)
            if match:
                result_text = match.group(0)
            else:
                return False, "", ""

            data = json.loads(result_text)

            if data.get("is_failing"):
                reason = data.get("reason", "Failure detected")
                correction = data.get("correction_prompt", "Discard approach.")
                self.memory.record_failure(reason, correction)
                return True, reason, correction
            return False, "", ""

        except Exception as e:
            # Flaw 4 Fix: Don't fail silently on critical API configuration errors
            error_str = str(e).lower()
            if (
                "api_key" in error_str
                or "auth" in error_str
                or "not found" in error_str
            ):
                raise RuntimeError(
                    f"\n[PANOPTICON FATAL ERROR] Missing or invalid API key for {self.target_agent}: {e}"
                )

            # For random network timeouts, ignore and try again next loop
            return False, "", ""

    def _route_to_llm(self, prompt: str) -> str:
        """Dynamically switch the meta-agent API based on the target CLI command, with intelligent fallbacks."""
        agent = self.target_agent

        # 1. Explicit matching based on command name
        if "agy" in agent or "gemini" in agent:
            if os.environ.get("GEMINI_API_KEY"):
                return self._call_gemini(prompt)
        elif "gpt" in agent or "codex" in agent or "openai" in agent:
            if os.environ.get("OPENAI_API_KEY"):
                return self._call_openai(prompt)
        elif "claude" in agent:
            if os.environ.get("ANTHROPIC_API_KEY"):
                return self._call_anthropic(prompt)

        # 2. Flaw 3 Fix: Intelligent Fallback if explicit match fails or agent is generic (e.g. 'python')
        if os.environ.get("ANTHROPIC_API_KEY"):
            return self._call_anthropic(prompt)
        elif os.environ.get("GEMINI_API_KEY"):
            return self._call_gemini(prompt)
        elif os.environ.get("OPENAI_API_KEY"):
            return self._call_openai(prompt)
        else:
            raise RuntimeError(
                "\n[PANOPTICON FATAL] No API keys found! Please set ANTHROPIC_API_KEY, GEMINI_API_KEY, or OPENAI_API_KEY."
            )

    def _call_anthropic(self, prompt: str) -> str:
        from anthropic import Anthropic

        client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        resp = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=150,
            temperature=0.0,
            system="Strict meta-agent. Output JSON.",
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text

    def _call_openai(self, prompt: str) -> str:
        from openai import OpenAI

        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "Strict meta-agent. Output JSON."},
                {"role": "user", "content": prompt},
            ],
        )
        return resp.choices[0].message.content

    def _call_gemini(self, prompt: str) -> str:
        import google.generativeai as genai

        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
        model = genai.GenerativeModel("gemini-1.5-flash")
        resp = model.generate_content(
            "Strict meta-agent. Output JSON.\n\n" + prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
            ),
        )
        return resp.text
