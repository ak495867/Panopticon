# Contributing to Panopticon

So you want to help build the Panopticon? Awesome. We need more guards in the watchtower.

## Adding a Custom Policy
Panopticon is highly modular. Want to build a policy that instantly drops the Guillotine if the AI attempts to write PHP code? Just extend the `BasePolicy` class in `panopticon/policies.py`.

```python
from .policies import BasePolicy
from typing import List, Dict, Tuple

class AntiPHPPolicy(BasePolicy):
    def evaluate(self, telemetry_stream: List[Dict]) -> Tuple[bool, str, str]:
        # Sniff the logs
        if "<?php" in telemetry_stream[-1].get("thought", ""):
            return True, "Ew, PHP.", "Stop writing PHP immediately and switch to Python or Rust."
            
        # Return (is_violating, reason, correction_prompt)
        return False, "", ""
```

## Developer Setup
We enforce quality around here. Panopticon uses `pytest`, `flake8`, and `black` in a strict CI/CD pipeline so we don't accidentally ship bugs to the thing designed to catch bugs.

1. Fork the repository and clone it.
2. Install the dev tools so you can actually do things:
   ```bash
   make install
   ```
3. Run the test suite (If this fails, your code is bad and you should feel bad):
   ```bash
   make test
   ```
4. Format and lint your code before committing:
   ```bash
   make format
   make lint
   ```
5. Open a Pull Request! We will review it shortly.
