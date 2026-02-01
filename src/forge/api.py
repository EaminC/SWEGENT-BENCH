import openai
from dotenv import load_dotenv
import os
from pathlib import Path
from typing import List, Dict, Optional

# Load .env: cwd first, then project root with override so project root wins
_project_root = Path(__file__).resolve().parent.parent.parent
_env_path = _project_root / ".env"
_cwd_env = Path.cwd() / ".env"
if _cwd_env.exists():
    load_dotenv(_cwd_env)
if _env_path.exists():
    load_dotenv(_env_path, override=True)  # project root overrides shell and cwd


def _getenv_stripped(key: str, default: str = "") -> str:
    v = os.getenv(key, default)
    if v is None:
        return default
    return str(v).strip().strip('"').strip("'")


class LLMClient:
    """Unified LLM calling interface"""
    
    def __init__(self, model: Optional[str] = None):
        """
        Initialize LLM client.
        Model and base URL are read from .env (MODEL, FORGE_BASE_URL) when not passed.
        """
        # Read at runtime so .env is always applied (and override=True above ensures .env wins)
        model_val = model or _getenv_stripped("MODEL", "OpenAI/gpt-4o")
        self.model = model_val or "OpenAI/gpt-4o"
        
        api_key = _getenv_stripped("FORGE_API_KEY")
        base_url = _getenv_stripped("FORGE_BASE_URL", "https://api.forge.tensorblock.co/v1") or "https://api.forge.tensorblock.co/v1"
        
        # Configure OpenAI for old version compatibility
        openai.api_key = api_key
        openai.api_base = base_url
        
        # Try to use new version if available
        try:
            from openai import OpenAI
            self.client = OpenAI(
                base_url=base_url,
                api_key=api_key,
            )
            self.use_new_api = True
        except (ImportError, TypeError):
            self.client = None
            self.use_new_api = False
    
    def chat(self, 
             messages: List[Dict[str, str]], 
             temperature: float = 0.7,
             max_tokens: Optional[int] = None) -> str:
        """
        Call LLM for chat
        
        Args:
            messages: Message list, format: [{"role": "user", "content": "..."}]
            temperature: Generation temperature, default 0.7
            max_tokens: Maximum tokens, default None
            
        Returns:
            LLM response content
        """
        try:
            if self.use_new_api:
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                return completion.choices[0].message.content
            else:
                # Use old OpenAI API
                kwargs = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                }
                if max_tokens:
                    kwargs["max_tokens"] = max_tokens
                
                completion = openai.ChatCompletion.create(**kwargs)
                return completion.choices[0].message.content
        except Exception as e:
            print(f"LLM call error: {e}")
            return ""
    
    def simple_chat(self,
                    user_message: str,
                    system_prompt: Optional[str] = None,
                    temperature: Optional[float] = None) -> str:
        """
        Simplified chat interface
        
        Args:
            user_message: User message
            system_prompt: System prompt, default None
            temperature: Generation temperature; default from .env AI_TEMPERATURE or 0.7
            
        Returns:
            LLM response content
        """
        if temperature is None:
            try:
                temperature = float((os.getenv("AI_TEMPERATURE") or "0.7").strip().strip('"').strip("'"))
            except (TypeError, ValueError):
                temperature = 0.7
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})
        
        return self.chat(messages, temperature=temperature)
    
    def list_models(self) -> List[str]:
        """
        List all available models
        
        Returns:
            List of model IDs
        """
        try:
            if self.use_new_api:
                models = self.client.models.list()
                return [model.id for model in models.data]
            else:
                # Old API doesn't support model listing the same way
                models = openai.Model.list()
                return [model.id for model in models.data]
        except Exception as e:
            print(f"Error getting model list: {e}")
            return []


# Test code
if __name__ == "__main__":
    llm = LLMClient()
    
    # Test simple chat
    response = llm.simple_chat("Hello!", system_prompt="You are a helpful assistant.")
    print(f"Response: {response}")
    
    # Test listing models
    models = llm.list_models()
    print(f"\nAvailable OpenAI models:")
    for model in models:
        if model.startswith("OpenAI/"):
            print(f"  - {model}")