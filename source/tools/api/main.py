from openai import OpenAI
from dotenv import load_dotenv
import os
import json
from pathlib import Path
from typing import List, Dict, Optional

# .env is in ../../../.env (relative to this file)
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

FORGE_API_KEY = os.getenv("FORGE_API_KEY")

# Initialize client
client = OpenAI(
    base_url="https://api.forge.tensorblock.co/v1",
    api_key=FORGE_API_KEY,
)


def chat(
    messages: List[Dict[str, str]],
    model: str = "tensorblock/gpt-4.1-mini",
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
) -> str:
    """
    Call LLM for chat.

    Args:
        messages: List of message dicts.
        model: Model name.
        temperature: Sampling temperature.
        max_tokens: Max tokens for response.
    """
    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return completion.choices[0].message.content


def get_models() -> List[str]:
    """Return available model IDs."""
    models = client.models.list()
    return [model.id for model in models.data]


def save_models_to_json(output_path: Optional[str] = None) -> str:
    """Save available models to JSON."""
    models = get_models()

    if output_path is None:
        output_path = Path(__file__).parent / "models.json"
    else:
        output_path = Path(output_path)

    data = {"models": models, "total_count": len(models)}

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return str(output_path)


if __name__ == "__main__":
    completion = client.chat.completions.create(
        model="OpenAI/gpt-4o",
        messages=[
            {"role": "developer", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
        ],
    )
    print(completion.choices[0].message)

    models = get_models()
    print(f"\nAvailable models ({len(models)}):")
    for model in models[:10]:
        print(f"  - {model}")

    json_path = save_models_to_json()
    print(f"\nModels saved to: {json_path}")