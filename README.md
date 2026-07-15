# PANOPTICON 👁️

> **The Cognitive Immune System (and glorified babysitter) for Autonomous CLI Agents.**

[![PyPI version](https://badge.fury.io/py/panopticon-cli.svg)](https://pypi.org/project/panopticon-cli/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/ak495867/Panopticon/actions/workflows/ci.yml/badge.svg)](https://github.com/ak495867/Panopticon/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

Autonomous CLI agents (like Claude Code, AutoGPT, and Antigravity) are amazing... right until they hallucinate, burn through $50 of your API credits, or confidently try to `rm -rf /` your hard drive. 

**Panopticon** is a zero-latency, non-blocking wrapper that silently watches your agent's terminal output. When the AI inevitably tries to do something incredibly stupid, Panopticon's **State Guillotine** drops. 

It intercepts the rogue process, uses a Meta-Agent to figure out why your AI is crying, and **forcefully injects the correction directly into the agent's live `stdin` stream** like a disappointed senior developer taking over the keyboard. Oh, and it saves that failure to a SQLite database so the agent never makes the exact same mistake twice.

## Why you need this

- **Native TTY Wrapping:** Slap it in front of any CLI. Loading spinners, ANSI colors, and interactive prompts still work perfectly. We just spy on them natively.
- **The Policy Cascade (Iron Dome):**
  - **Level 1 (Blacklist):** Instant, zero-cost kills for destructive actions. Because your AI *will* try to drop your production database eventually.
  - **Level 2 (Fuzzy Heuristics):** Zero-cost math thresholds that catch repetitive loops. Stops the agent from running `cat missing_file.py` 300 times in a row.
  - **Level 3 (Universal Semantic Logic):** Streams a sliding-window of the terminal to a Meta-Agent (Claude, GPT, or Gemini) to judge your sub-agent's poor life choices.
- **True Live Injection:** We don't just kill the agent and leave you hanging. Panopticon literally types the course-correction prompt into the interactive terminal for you, saving the session.
- **Persistent Semantic Memory:** AI agents have goldfish memory. We use SQLite and Jaccard keyword routing to permanently scar them with their past failures so they actually learn.

## Quick Start

```bash
# Install globally from PyPI
pip install panopticon-cli

# Export your preferred API Key (Panopticon dynamically routes to whatever you actually pay for)
export OPENAI_API_KEY="sk-..."
# OR export ANTHROPIC_API_KEY="..."
# OR export GEMINI_API_KEY="..."

# Slap it in front of your agent!
panopticon claude
# OR
panopticon agy
```

See [USAGE.md](USAGE.md) for deeper configuration so you can start dropping the Guillotine.
