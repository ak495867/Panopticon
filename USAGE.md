# Usage Guide (How to babysit your AI)

Panopticon is designed to be completely invisible until your agent decides to jump off a logical cliff. 

## 1. Basic Wrapping
Literally just type `panopticon` before whatever terminal command you normally run. That's it.
```bash
panopticon claude
panopticon agy --task "build me a startup"
panopticon python my_sketchy_ai_script.py
```

## 2. Setting up the Universal Sentinel (The Big Brain)
The Level 3 Semantic Policy uses an LLM to analyze your agent's terminal logs. Because we don't want to force you into a specific ecosystem, Panopticon is completely **model-agnostic**. 

Just throw whatever API key you have into your environment variables, and Panopticon will automatically find it and use it. 
```bash
# Windows (PowerShell)
$env:OPENAI_API_KEY="sk-..."
$env:ANTHROPIC_API_KEY="sk-ant-..."
$env:GEMINI_API_KEY="AIza..."

# Mac/Linux (or just use a .env file like a civilized person)
export OPENAI_API_KEY="sk-..."
```
*Note: Panopticon uses overlapping sliding windows and truncates context heavily. Babysitting your agent for an hour typically costs less than a gumball.*

## 3. Persistent Memory & Live Injection
When Panopticon triggers the Guillotine, it doesn't just crash. Here is the magic:
1. It carves the failure into a local SQLite database (`panopticon_memory.db`) using Write-Ahead Logging.
2. It sends a `SIGINT` to slap the runaway process in the face, and then **injects** the correction text directly into the agent's active `stdin` stream.

You do not need to manage the DB or restart your agent. The immune system handles the recovery natively while you sip your coffee.

## 4. Reading the Telemetry
If you are building a fancy dashboard (or just like watching the Matrix code fall), you can tail the live telemetry file:
```bash
tail -f panopticon_telemetry.jsonl
```
This file outputs clean JSON events (`start`, `step`, `interrupt`, `guillotine`). And yes, it's bounded by a sliding queue so it doesn't leak memory and crash your laptop after 3 days.
