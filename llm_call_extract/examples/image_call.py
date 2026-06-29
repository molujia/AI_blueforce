from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from llm_client import ModelRouter, image_part, image_to_data_url, text_part


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a multimodal LLM call with one local image.")
    parser.add_argument("--task", default="reply_generation")
    parser.add_argument("--image", required=True)
    parser.add_argument("--prompt", default="Describe the image. Return JSON with keys saw_image and description.")
    args = parser.parse_args()

    router = ModelRouter()
    response = router.get_chat_model(args.task).invoke(
        [
            {"role": "system", "content": "Return strict JSON only."},
            {"role": "user", "content": [text_part(args.prompt), image_part(image_to_data_url(args.image))]},
        ]
    )
    print(response.content)
    print(json.dumps(response.usage_metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
