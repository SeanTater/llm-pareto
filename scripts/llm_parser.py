#!/usr/bin/env python3
"""
LLM-based parsing using Claude CLI
"""

import subprocess
import json
import re
from typing import Dict, Any, Optional


class LLMParser:
    """Wrapper for Claude CLI to parse HTML/text into structured data"""

    def __init__(self, model: str = "sonnet"):
        """
        Initialize parser

        Args:
            model: Claude model to use (sonnet, opus, haiku)
        """
        self.model = model

    def parse(self, prompt: str, max_retries: int = 2) -> Dict[str, Any]:
        """
        Parse with LLM and return structured JSON

        Args:
            prompt: Prompt to send to Claude
            max_retries: Number of retries if parsing fails

        Returns:
            Parsed JSON data

        Raises:
            LLMParseError: If parsing fails after retries
        """
        for attempt in range(max_retries):
            try:
                # Call Claude CLI
                result = subprocess.run(
                    ["claude", "--model", self.model],
                    input=prompt,
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if result.returncode != 0:
                    raise LLMParseError(f"Claude CLI failed: {result.stderr}")

                response = result.stdout

                # Extract JSON from response
                data = self._extract_json(response)

                return data

            except json.JSONDecodeError as e:
                if attempt < max_retries - 1:
                    print(f"JSON parse failed (attempt {attempt + 1}/{max_retries}), retrying...")
                    continue
                raise LLMParseError(f"Failed to parse JSON after {max_retries} attempts: {e}")

            except subprocess.TimeoutExpired:
                raise LLMParseError("Claude CLI timed out after 60s")

        raise LLMParseError("Max retries exceeded")

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
    # Truncate HTML if too long (keep first 15k chars)
    if len(html) > 15000:
        html = html[:15000] + "\n... [truncated]"

    prompt = f"""Extract pricing information for ALL {provider} language models from the HTML below.

Return a JSON array with this exact structure:
[
  {{
    "model_id": "gpt-4o",
    "model_name": "GPT-4o",
    "input_per_1m_tokens": 5.00,
    "output_per_1m_tokens": 15.00,
    "notes": "any relevant notes or context"
  }}
]

Important:
- Convert all prices to dollars per 1 million tokens
- Use lowercase-with-hyphens for model_id (e.g., "gpt-4o", "claude-3-5-sonnet")
- Include only current production models (not deprecated/legacy)
- If a model has multiple pricing tiers, use the standard tier
- Return ONLY the JSON array, no other text

HTML:
{html}
"""
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
    parser = LLMParser()

    # Test with simple JSON extraction
    test_prompt = """
    Return a JSON object with pricing for GPT-4:
    {
      "model": "gpt-4",
      "input": 30.0,
      "output": 60.0
    }
    """

    try:
        result = parser.parse(test_prompt)
        print("✓ Parser working!")
        print(json.dumps(result, indent=2))
    except LLMParseError as e:
        print(f"✗ Parser failed: {e}")
