import openai
from dotenv import load_dotenv
import os
from typing import List, Dict, Optional

# .env is in ../../.env
load_dotenv()

FORGE_API_KEY = os.getenv("FORGE_API_KEY")


class LLMClient:
    """Unified LLM calling interface"""
    
    def __init__(self, model: str = "OpenAI/gpt-4o"):
        """
        Initialize LLM client
        
        Args:
            model: Model name to use, default is OpenAI/gpt-4o
        """
        self.model = model
        
        # Configure OpenAI for old version compatibility
        openai.api_key = FORGE_API_KEY
        openai.api_base = "https://api.forge.tensorblock.co/v1"
        
        # Try to use new version if available
        try:
            from openai import OpenAI
            self.client = OpenAI(
                base_url="https://api.forge.tensorblock.co/v1", 
                api_key=FORGE_API_KEY,  
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
                    temperature: float = 0.7) -> str:
        """
        Simplified chat interface
        
        Args:
            user_message: User message
            system_prompt: System prompt, default None
            temperature: Generation temperature, default 0.7
            
        Returns:
            LLM response content
        """
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