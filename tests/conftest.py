"""Shared fixtures for the Market Intelligence test suite.

Smoke tests live in this directory and run without a database, API keys,
or real network calls. They exist to guarantee the module tree loads and
the rule-based / deterministic code paths still work end-to-end.
"""

import os
import sys

# Ensure project root is on sys.path so imports like `from config import ...` work.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
