#!/usr/bin/env python3
"""
Main orchestrator for LLM data collection

Usage:
    python collect_data.py --dry-run    # Test without modifying files
    python collect_data.py              # Update data/models.json
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Add scrapers to path
sys.path.append(str(Path(__file__).parent))

from scrapers.pricing import PricingScraper, ScraperError


class DataCollector:
    """Main orchestrator for data collection"""

    def __init__(self, data_dir: Path, dry_run: bool = False):
        """
        Initialize collector

        Args:
            data_dir: Path to data directory
            dry_run: If True, don't modify files
        """
        self.data_dir = data_dir
        self.dry_run = dry_run
        self.models_file = data_dir / "models.json"
        self.changes_log = []

    def load_existing_data(self) -> Dict[str, Any]:
        """Load existing models.json"""
        if self.models_file.exists():
            with open(self.models_file) as f:
                return json.load(f)
        return {"models": [], "last_updated": None}

    def collect_pricing(self) -> Dict[str, Any]:
        """Collect pricing data from all providers"""
        print("\n" + "="*60)
        print("COLLECTING PRICING DATA")
        print("="*60 + "\n")

        scraper = PricingScraper()
        return scraper.scrape()

    def merge_pricing(self, existing_data: Dict[str, Any], pricing_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge scraped pricing into existing model data

        Args:
            existing_data: Current models.json content
            pricing_data: Scraped pricing from all providers

        Returns:
            Updated model data
        """
        print("\n" + "="*60)
        print("MERGING PRICING DATA")
        print("="*60 + "\n")

        # Index existing models by ID
        models_by_id = {m["id"]: m for m in existing_data.get("models", [])}

        # Process each provider's pricing
        for provider_name, provider_data in pricing_data.items():
            if "error" in provider_data:
                print(f"⊘ Skipping {provider_name} (error during scrape)")
                continue

            for model_data in provider_data["models"]:
                model_id = model_data["model_id"]

                # Check if model exists
                if model_id in models_by_id:
                    # Update pricing
                    existing_model = models_by_id[model_id]

                    old_input = existing_model.get("pricing", {}).get("input_per_1m_tokens")
                    new_input = model_data["input_per_1m_tokens"]

                    old_output = existing_model.get("pricing", {}).get("output_per_1m_tokens")
                    new_output = model_data["output_per_1m_tokens"]

                    if old_input != new_input or old_output != new_output:
                        self.changes_log.append(
                            f"  Updated {model_id} pricing: "
                            f"${old_input or '?'}/{old_output or '?'} → "
                            f"${new_input}/{new_output}"
                        )

                    # Update pricing
                    models_by_id[model_id]["pricing"] = {
                        "input_per_1m_tokens": model_data["input_per_1m_tokens"],
                        "output_per_1m_tokens": model_data["output_per_1m_tokens"],
                        "source": provider_data["source"]
                    }

                else:
                    # New model - create minimal entry
                    print(f"  + New model discovered: {model_id}")
                    self.changes_log.append(f"  Added new model: {model_id}")

                    models_by_id[model_id] = {
                        "id": model_id,
                        "name": model_data["model_name"],
                        "provider": provider_name,
                        "family": self._guess_family(model_data["model_name"]),
                        "pricing": {
                            "input_per_1m_tokens": model_data["input_per_1m_tokens"],
                            "output_per_1m_tokens": model_data["output_per_1m_tokens"],
                            "source": provider_data["source"]
                        },
                        "benchmarks": {}
                    }

        # Convert back to list
        updated_data = {
            "models": list(models_by_id.values()),
            "last_updated": datetime.now().isoformat()
        }

        return updated_data

    def _guess_family(self, model_name: str) -> str:
        """Guess model family from name"""
        name_lower = model_name.lower()
        if "gpt" in name_lower:
            if "gpt-4" in name_lower:
                return "GPT-4"
            return "GPT-3"
        elif "claude" in name_lower:
            return "Claude"
        elif "gemini" in name_lower:
            return "Gemini"
        elif "llama" in name_lower:
            return "Llama"
        return "Other"

    def save_data(self, data: Dict[str, Any]):
        """Save updated data to models.json"""
        if self.dry_run:
            print("\n[DRY RUN] Would save to:", self.models_file)
            return

        with open(self.models_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"\n✓ Saved to {self.models_file}")

    def print_summary(self, pricing_data: Dict[str, Any]):
        """Print summary of what was collected"""
        print("\n" + "="*60)
        print("COLLECTION SUMMARY")
        print("="*60 + "\n")

        # Scraping results
        print("Scraping Results:")
        for provider, data in pricing_data.items():
            if "error" in data:
                print(f"  ✗ {provider}: {data['error']}")
            else:
                print(f"  ✓ {provider}: {len(data['models'])} models")

        # Changes
        if self.changes_log:
            print("\nChanges:")
            for change in self.changes_log:
                print(change)
        else:
            print("\nNo changes detected")

        if self.dry_run:
            print("\n[DRY RUN MODE] No files were modified")

    def run(self):
        """Main execution flow"""
        try:
            # Load existing data
            existing_data = self.load_existing_data()
            print(f"Loaded {len(existing_data.get('models', []))} existing models")

            # Collect pricing
            pricing_data = self.collect_pricing()

            # Merge data
            updated_data = self.merge_pricing(existing_data, pricing_data)

            # Save
            self.save_data(updated_data)

            # Print summary
            self.print_summary(pricing_data)

            return 0

        except Exception as e:
            print(f"\n✗ FATAL ERROR: {e}")
            import traceback
            traceback.print_exc()
            return 1


def main():
    parser = argparse.ArgumentParser(description="Collect LLM pricing and benchmark data")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test mode - don't modify files"
    )
    args = parser.parse_args()

    # Find data directory
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / "data"

    if not data_dir.exists():
        print(f"Error: Data directory not found: {data_dir}")
        return 1

    # Run collector
    collector = DataCollector(data_dir, dry_run=args.dry_run)
    return collector.run()


if __name__ == "__main__":
    sys.exit(main())
