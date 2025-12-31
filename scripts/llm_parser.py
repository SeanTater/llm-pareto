#!/usr/bin/env python3
"""
LLM-based parsing using Ollama
"""

import subprocess
import json
import re
import requests
from typing import Dict, Any, Optional, List
from pydantic import BaseModel


class PricingModel(BaseModel):
    """Schema for a single model's pricing"""
    model_id: str
    model_name: str
    input_per_1m_tokens: float
    output_per_1m_tokens: float
    notes: str = ""


class PricingResponse(BaseModel):
    """Schema for list of pricing models"""
    models: List[PricingModel]


class LLMParser:
    """Wrapper for Ollama to parse HTML/text into structured data"""

    def __init__(self, model: str = "ministral-3:latest", backend: str = "ollama", ollama_url: str = "http://localhost:11437"):
        """
        Initialize parser

        Args:
            model: Model to use (e.g., "ministral-3:latest", "ministral-3:8b")
            backend: Backend to use ("ollama" or "claude")
            ollama_url: Ollama API endpoint
        """
        self.model = model
        self.backend = backend
        self.ollama_url = ollama_url

    def parse(self, prompt: str, max_retries: int = 2, schema: Optional[type[BaseModel]] = None) -> Dict[str, Any]:
        """
        Parse with LLM and return structured JSON

        Args:
            prompt: Prompt to send to LLM
            max_retries: Number of retries if parsing fails
            schema: Optional Pydantic model to constrain output format

        Returns:
            Parsed JSON data

        Raises:
            LLMParseError: If parsing fails after retries
        """
        for attempt in range(max_retries):
            try:
                if self.backend == "ollama":
                    response = self._call_ollama(prompt, schema)
                elif self.backend == "claude":
                    response = self._call_claude(prompt)
                else:
                    raise LLMParseError(f"Unknown backend: {self.backend}")

                # Extract JSON from response
                data = self._extract_json(response)

                # Validate against schema if provided
                if schema and self.backend == "ollama":
                    validated = schema.model_validate(data)
                    return validated.model_dump()

                return data

            except json.JSONDecodeError as e:
                if attempt < max_retries - 1:
                    print(f"JSON parse failed (attempt {attempt + 1}/{max_retries}), retrying...")
                    continue
                raise LLMParseError(f"Failed to parse JSON after {max_retries} attempts: {e}")

        raise LLMParseError("Max retries exceeded")

    def _call_ollama(self, prompt: str, schema: Optional[type[BaseModel]] = None) -> str:
        """Call Ollama API with optional Pydantic schema constraint"""
        try:
            # Prepare request body
            body = {
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }

            # Add schema if provided, otherwise just request JSON
            if schema:
                body["format"] = schema.model_json_schema()
            else:
                body["format"] = "json"

            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=body,
                timeout=120  # Longer timeout for GPU
            )
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        except requests.RequestException as e:
            raise LLMParseError(f"Ollama API failed: {e}")

    def _call_claude(self, prompt: str) -> str:
        """Call Claude CLI"""
        try:
            result = subprocess.run(
                ["claude", "--model", self.model],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode != 0:
                raise LLMParseError(f"Claude CLI failed: {result.stderr}")
            return result.stdout
        except subprocess.TimeoutExpired:
            raise LLMParseError("Claude CLI timed out after 60s")

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """
        Extract JSON from LLM response

        LLMs often wrap JSON in markdown code blocks, so we try:
        1. Parse the full text as JSON
        2. Extract from ```json...``` blocks
        3. Extract from {...} or [...]
        """
        # Try parsing directly
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try extracting from code block
        json_block_match = re.search(r'```json\s*\n(.*?)\n```', text, re.DOTALL)
        if json_block_match:
            try:
                return json.loads(json_block_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try extracting any JSON object or array
        json_match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        raise json.JSONDecodeError(f"No valid JSON found in response: {text[:200]}...", text, 0)


class LLMParseError(Exception):
    """Raised when LLM parsing fails"""
    pass


def create_pricing_prompt(html: str, provider: str) -> str:
    """
    Create prompt for extracting pricing data

    Args:
        html: HTML content to parse
        provider: Provider name (e.g., "OpenAI", "Anthropic")

    Returns:
        Formatted prompt for LLM
    """
    # Truncate HTML if too long (keep first 50k chars for better coverage)
    if len(html) > 50000:
        html = html[:50000] + "\n... [truncated]"

    prompt = f"""Extract pricing for ALL {provider} language models from the HTML below.

Return a JSON object with this exact structure:
{{
  "models": [
    {{
      "model_id": "gpt-4o",
      "model_name": "GPT-4o",
      "input_per_1m_tokens": 5.00,
      "output_per_1m_tokens": 15.00,
      "notes": ""
    }}
  ]
}}

RULES:
1. Convert all prices to dollars per 1 million tokens
2. Use lowercase-with-hyphens for model_id
3. Include only current production models
4. If multiple tiers exist, use standard tier
5. Leave notes empty unless there's important context

HTML:
{html}"""
    return prompt


def create_model_card_prompt(html: str, model_name: str) -> str:
    """
    Create prompt for extracting benchmark data from HuggingFace model card

    Args:
        html: HTML or markdown content to parse
        model_name: Model name for context

    Returns:
        Formatted prompt for LLM
    """
    # Truncate if too long
    if len(html) > 15000:
        html = html[:15000] + "\n... [truncated]"

    prompt = f"""Extract benchmark scores for {model_name} from the model card below.

Return a JSON object with this structure:
{{
  "model_name": "{model_name}",
  "parameters_billions": 70.0,
  "benchmarks": {{
    "mmlu": 85.2,
    "humaneval": 80.5,
    "gsm8k": 95.1
  }},
  "notes": "any relevant context"
}}

Common benchmark names (use these keys if found):
- mmlu: MMLU score (0-100)
- humaneval: HumanEval pass@1 (0-100)
- gsm8k: GSM8K score (0-100)
- bbh: Big-Bench Hard (0-100)
- mbpp: MBPP pass@1 (0-100)

Important:
- Only include benchmarks explicitly mentioned
- Scores should be 0-100 range (convert percentages if needed)
- If parameter count is mentioned, extract it
- Return ONLY the JSON object, no other text

Content:
{html}
"""
    return prompt


# Example usage
if __name__ == "__main__":
    # Test Ollama
    print("Testing Ollama parser...")
    parser = LLMParser(
        model="ministral-3:latest",
        backend="ollama",
        ollama_url="http://localhost:11437"
    )

    # Test with simple JSON extraction
    test_prompt = """Return ONLY a JSON object (no other text) with pricing for GPT-4:
{
  "model": "gpt-4",
  "input": 30.0,
  "output": 60.0
}"""

    try:
        print("Calling Ollama...")
        result = parser.parse(test_prompt)
        print("✓ Parser working!")
        print(json.dumps(result, indent=2))
    except LLMParseError as e:
        print(f"✗ Parser failed: {e}")
