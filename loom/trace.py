"""JSONL trace: one event per line, one file per run."""
import json
import time
from pathlib import Path

# $ per million tokens: (max prompt tokens for this tier, input, output)
PRICES = {"claude-haiku-5-5": [(100_000, 0.10, 0.50), (float("inf"), 0.50, 2.50)]}


def cost(model, usage):
    """Dollar cost of one response, or None for a model without a price entry."""
    tiers = PRICES.get(model)
    if not tiers:
        return None
    write = getattr(usage, "cache_creation_input_tokens", 0) or 0
    read = getattr(usage, "cache_read_input_tokens", 0) or 0
    prompt = usage.input_tokens + write + read
    i, o = next((i, o) for limit, i, o in tiers if prompt <= limit)
    return (usage.input_tokens * i + write * i * 1.25 + read * i * 0.1 + usage.output_tokens * o) / 1e6


class Trace:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.f = self.path.open("a")

    def __call__(self, event, **data):
        self.f.write(json.dumps({"t": round(time.time(), 3), "event": event, **data}, default=str) + "\n")
        self.f.flush()
