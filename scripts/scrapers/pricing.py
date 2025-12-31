#!/usr/bin/env python3
"""
Pricing scrapers for LLM providers
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from scrapers.base import BaseScraper, ScraperError
from llm_parser import LLMParser, LLMParseError, create_pricing_prompt, PricingResponse
from screenshot import screenshot_url
from typing import Dict, List, Any


class PricingScraper(BaseScraper):
    """Scrapes pricing information from provider websites"""

    def __init__(self, use_ollama: bool = True, use_vision: bool = False, vision_model: str = "qwen3-vl:8b"):
        super().__init__()
        self.use_vision = use_vision

        if use_ollama:
            # Use Ollama with GPU proxy
            model = vision_model if use_vision else "ministral-3:latest"
            self.parser = LLMParser(
                model=model,
                backend="ollama",
                ollama_url="http://localhost:11437"
            )
            print(f"Using Ollama at localhost:11437 with {model}")
        else:
            # Fallback to Claude CLI
            self.parser = LLMParser(model="sonnet", backend="claude")
            print("Using Claude CLI")

    def _scrape_with_vision(self, url: str, provider: str) -> List[Dict[str, Any]]:
        """Helper to scrape using screenshot + vision model"""
        print(f"Taking screenshot of {url}...")
        image_b64 = screenshot_url(url)

        print(f"Extracting pricing with vision model...")
        prompt = f"""Extract ALL {provider} language model pricing from this pricing page screenshot.

Return a JSON object with this structure:
{{
  "models": [
    {{
      "model_id": "model-name",
      "model_name": "Model Name",
      "input_per_1m_tokens": 5.00,
      "output_per_1m_tokens": 15.00,
      "notes": ""
    }}
  ]
}}

IMPORTANT:
- Convert all prices to dollars per 1 million tokens
- Use lowercase-with-hyphens for model_id
- Extract ONLY {provider} models
- Include all production models visible in the screenshot"""

        result = self.parser.parse(prompt, schema=PricingResponse, image_base64=image_b64)
        return result.get('models', [])

    def scrape_openai(self) -> Dict[str, Any]:
        """
        Scrape OpenAI pricing

        Returns:
            Dict with models and metadata
        """
        url = "https://openai.com/api/pricing/"

        try:
            print(f"Fetching OpenAI pricing from {url}...")
            html = self.fetch_url(url)

            print("Parsing with Ollama using Pydantic schema...")
            prompt = create_pricing_prompt(html, "OpenAI")
            result = self.parser.parse(prompt, schema=PricingResponse)

            models = result.get('models', [])
            if not models:
                raise ScraperError("No models found in response")

            print(f"✓ Found {len(models)} OpenAI models")

            return {
                "provider": "OpenAI",
                "models": models,
                "source": {
                    "url": url,
                    "type": "primary",
                    "collected": self._now(),
                    "scrape_method": "llm"
                }
            }

        except LLMParseError as e:
            raise ScraperError(f"Failed to parse OpenAI pricing: {e}")

    def scrape_anthropic(self) -> Dict[str, Any]:
        """Scrape Anthropic pricing"""
        url = "https://www.anthropic.com/pricing"

        try:
            # Use vision if enabled, otherwise try HTML
            if self.use_vision:
                models = self._scrape_with_vision(url, "Anthropic")
            else:
                print(f"Fetching Anthropic pricing from {url}...")
                html = self.fetch_url(url)

                print("Parsing with Ollama using Pydantic schema...")
                prompt = create_pricing_prompt(html, "Anthropic")
                result = self.parser.parse(prompt, schema=PricingResponse)
                models = result.get('models', [])

            if not models:
                raise ScraperError("No models found in response")

            print(f"✓ Found {len(models)} Anthropic models")

            return {
                "provider": "Anthropic",
                "models": models,
                "source": {
                    "url": url,
                    "type": "primary",
                    "collected": self._now(),
                    "scrape_method": "vision" if self.use_vision else "llm"
                }
            }

        except LLMParseError as e:
            raise ScraperError(f"Failed to parse Anthropic pricing: {e}")

    def scrape_google(self) -> Dict[str, Any]:
        """Scrape Google AI pricing"""
        url = "https://ai.google.dev/pricing"

        try:
            print(f"Fetching Google AI pricing from {url}...")
            html = self.fetch_url(url)

            print("Parsing with Ollama using Pydantic schema...")
            prompt = create_pricing_prompt(html, "Google")
            result = self.parser.parse(prompt, schema=PricingResponse)

            models = result.get('models', [])
            if not models:
                raise ScraperError("No models found in response")

            print(f"✓ Found {len(models)} Google models")

            return {
                "provider": "Google",
                "models": models,
                "source": {
                    "url": url,
                    "type": "primary",
                    "collected": self._now(),
                    "scrape_method": "llm"
                }
            }

        except LLMParseError as e:
            raise ScraperError(f"Failed to parse Google pricing: {e}")

    def scrape(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Scrape all providers

        Returns:
            Dict mapping provider names to their pricing data
        """
        results = {}
        providers = [
            ("OpenAI", self.scrape_openai),
            ("Anthropic", self.scrape_anthropic),
            ("Google", self.scrape_google)
        ]

        for provider_name, scraper_func in providers:
            try:
                results[provider_name] = scraper_func()
            except ScraperError as e:
                print(f"✗ {provider_name} failed: {e}")
                results[provider_name] = {"error": str(e)}

        return results

    def _now(self) -> str:
        """Get current ISO timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()


# Test harness
if __name__ == "__main__":
    import json

    print("=== Testing Pricing Scraper with Vision ===\n")

    # Test with vision model for Anthropic (complex JavaScript page)
    scraper = PricingScraper(use_vision=True, vision_model="qwen3-vl:8b")

    print("Testing Anthropic scraper with vision...\n")
    try:
        result = scraper.scrape_anthropic()
        print("\n" + "="*50)
        print("RESULT:")
        print(json.dumps(result, indent=2))
        print("="*50)
    except ScraperError as e:
        print(f"\n✗ FAILED: {e}")
