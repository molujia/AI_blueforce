from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from llm_client import ModelRouter


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a plain text LLM call.")
    parser.add_argument("--task", default="triage_extract")
    parser.add_argument("--prompt", default="Return JSON with keys status and message. status should be OK.")
    args = parser.parse_args()

    router = ModelRouter()
    response = router.get_chat_model(args.task).invoke(
        [
            {"role": "system", "content": "Return strict JSON only."},
            {"role": "user", "content": args.prompt},
        ]
    )
    print(response.content)
    print(json.dumps(response.usage_metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
