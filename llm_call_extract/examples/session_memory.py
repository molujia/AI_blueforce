from __future__ import annotations

import argparse
import secrets
import string
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from llm_client import ModelRouter


def random_token(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def main() -> None:
    parser = argparse.ArgumentParser(description="Check whether a Responses session remembers a previous turn.")
    parser.add_argument("--task", default="sop_workflow_analysis")
    args = parser.parse_args()

    marker = random_token()
    session = ModelRouter().begin_session(args.task)

    first = session.invoke(
        [
            {"role": "system", "content": "Return strict JSON only."},
            {"role": "user", "content": f"Remember this random marker: {marker}. Return JSON with status OK."},
        ]
    )
    second = session.invoke(
        [
            {
                "role": "user",
                "content": "What random marker did I ask you to remember? Return JSON with key marker.",
            }
        ]
    )

    print(f"session_id={session.session_id}")
    print(f"expected_marker={marker}")
    print("first_response:")
    print(first.content)
    print("second_response:")
    print(second.content)


if __name__ == "__main__":
    main()
