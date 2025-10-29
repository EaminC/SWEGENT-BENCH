Forge API Integration Guide

This document explains how to use the Forge API as a drop-in replacement for the OpenAI API.
The Forge endpoint is fully OpenAI-compatible, allowing you to switch models or backends with minimal code changes.

⸻

Usage Example

from openai import OpenAI

# Initialize client with Forge endpoint
client = OpenAI(
    base_url="https://api.forge.tensorblock.co/v1",
    api_key=FORGE_API_KEY,  # Replace with your Forge API key
)

# Example: chat completion request
completion = client.chat.completions.create(
    model="OpenAI/gpt-4o",  # or your custom Forge model name
    messages=[
        {"role": "developer", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"}
    ]
)

print(completion.choices[0].message)


⸻

Difference from the OpenAI API

Feature	OpenAI API	Forge API
Base URL	https://api.openai.com/v1	https://api.forge.tensorblock.co/v1
SDK	openai (official)	openai (same SDK, fully compatible)
API Key Variable	OPENAI_API_KEY	FORGE_API_KEY
Models	gpt-4o, gpt-3.5-turbo, etc.	OpenAI/gpt-4o, or any custom Forge-hosted model
Compatibility	Native OpenAI API	100% OpenAI-compatible

Only the base_url and api_key need to be changed — the rest of your code remains exactly the same.