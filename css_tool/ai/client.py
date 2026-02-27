"""
AI Client Module
Handles communication with Ollama
"""

import json
import requests
from typing import Optional, Dict
from dataclasses import dataclass


@dataclass
class RefactoringResult:
    """Result from AI refactoring"""
    success: bool
    refactored_css: Optional[str]
    error: Optional[str]
    tokens_used: int = 0
    
    def __str__(self):
        if self.success:
            return f"Success ({self.tokens_used} tokens)"
        return f"Error: {self.error}"


class OllamaClient:
    """Client for Ollama API"""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen2.5-coder:0.5b"):
        """
        Initialize Ollama client
        
        Args:
            base_url: Ollama API base URL
            model: Model name to use
        """
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = 600
    
    def is_available(self) -> bool:
        """Check if Ollama is available"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def get_models(self) -> list:
        """Get list of available models"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
            return []
        except Exception:
            return []
    
    def generate(self, prompt: str, system: Optional[str] = None) -> Dict:
        """
        Generate response from Ollama
        
        Args:
            prompt: User prompt
            system: System prompt (optional)
        
        Returns:
            Response dictionary
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "top_p": 0.9,
                "num_predict": 4096
            }
        }
        
        if system:
            payload["system"] = system
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
        
        except requests.exceptions.Timeout:
            return {"error": "Request timed out"}
        except requests.exceptions.ConnectionError:
            return {"error": "Could not connect to Ollama"}
        except Exception as e:
            return {"error": str(e)}
