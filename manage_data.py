#!/usr/bin/env python3
"""
Data management tool for LLM Pareto Frontier project.

Handles adding models and benchmarks to the dataset with validation,
conflict detection, and dry-run mode.
"""

import json
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
from datetime import datetime


class DataManager:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.models_dir = data_dir / 'models'
        self.benchmarks_dir = data_dir / 'benchmarks'

    def load_all_benchmarks(self) -> Dict[str, dict]:
        """Load all benchmarks from category files."""
        all_benchmarks = {}
        for category_file in self.benchmarks_dir.glob('*.json'):
            if category_file.name == 'categories.json':
                continue
            with open(category_file) as f:
                data = json.load(f)
                all_benchmarks.update(data.get('benchmarks', {}))
        return all_benchmarks

    def load_all_models(self) -> Dict[str, List[dict]]:
        """Load all models grouped by file."""
        models_by_file = {}
        for provider_dir in self.models_dir.iterdir():
            if provider_dir.is_file() and provider_dir.suffix == '.json':
                # Top-level provider files (google.json, meta.json)
                with open(provider_dir) as f:
                    data = json.load(f)
                    models_by_file[str(provider_dir.relative_to(self.data_dir))] = data
            elif provider_dir.is_dir():
                # Provider subdirectories (openai/, anthropic/, qwen/)
                for model_file in provider_dir.glob('*.json'):
                    with open(model_file) as f:
                        data = json.load(f)
                        models_by_file[str(model_file.relative_to(self.data_dir))] = data
        return models_by_file

    def find_model_file(self, model_id: str) -> Tuple[Path, dict]:
        """Find which file contains a model by ID."""
        models_by_file = self.load_all_models()
        for file_path, data in models_by_file.items():
            for model in data.get('models', []):
                if model['id'] == model_id:
                    return self.data_dir / file_path, data
        return None, None

    def query_model(self, model_id: str) -> dict:
        """Query a model by ID and return its data."""
        models_by_file = self.load_all_models()
        for file_path, data in models_by_file.items():
            for model in data.get('models', []):
                if model['id'] == model_id:
                    return {
                        'model': model,
                        'file': file_path,
                        'provider': data.get('provider', 'Unknown')
                    }
        return None

    def list_models(self, provider: str = None, family: str = None) -> List[dict]:
        """List all models, optionally filtered by provider or family."""
        models_by_file = self.load_all_models()
        all_models = []
        for file_path, data in models_by_file.items():
            for model in data.get('models', []):
                if provider and model.get('provider') != provider:
                    continue
                if family and model.get('family') != family:
                    continue
                all_models.append({
                    'id': model['id'],
                    'name': model['name'],
                    'provider': model.get('provider', 'Unknown'),
                    'family': model.get('family', 'Unknown'),
                    'parameters_billions': model.get('parameters_billions'),
                    'active_parameters_billions': model.get('active_parameters_billions'),
                    'file': file_path
                })
        return sorted(all_models, key=lambda x: (x['provider'], x['family'], x['id']))

    def validate_benchmarks_exist(self, benchmark_ids: Set[str]) -> Tuple[bool, List[str]]:
        """Check if all benchmark IDs exist in benchmark files."""
        all_benchmarks = self.load_all_benchmarks()
        missing = [bid for bid in benchmark_ids if bid not in all_benchmarks]
        return len(missing) == 0, missing

    def add_benchmarks(self, input_data: dict, dry_run: bool = True) -> dict:
        """Add benchmarks to appropriate category files."""
        results = {
            'added': [],
            'updated': [],
            'skipped': [],
            'errors': []
        }

        benchmarks_to_add = input_data.get('benchmarks', {})

        # Load existing benchmarks
        all_existing = self.load_all_benchmarks()

        for bench_id, bench_data in benchmarks_to_add.items():
            category = bench_data.get('category', 'knowledge')
            category_file = self.benchmarks_dir / f'{category}.json'

            if not category_file.exists():
                results['errors'].append(f"Category file not found: {category}.json")
                continue

            # Check if benchmark already exists
            if bench_id in all_existing:
                existing = all_existing[bench_id]
                if existing == bench_data:
                    results['skipped'].append(f"{bench_id} (identical)")
                else:
                    results['updated'].append(f"{bench_id} (data differs)")
                    if not dry_run:
                        self._update_benchmark(category_file, bench_id, bench_data)
            else:
                results['added'].append(bench_id)
                if not dry_run:
                    self._add_benchmark(category_file, bench_id, bench_data)

        return results

    def _add_benchmark(self, category_file: Path, bench_id: str, bench_data: dict):
        """Add a benchmark to a category file."""
        with open(category_file) as f:
            data = json.load(f)

        data['benchmarks'][bench_id] = bench_data

        with open(category_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _update_benchmark(self, category_file: Path, bench_id: str, bench_data: dict):
        """Update an existing benchmark."""
        with open(category_file) as f:
            data = json.load(f)

        data['benchmarks'][bench_id] = bench_data

        with open(category_file, 'w') as f:
            json.dump(data, f, indent=2)

    def add_models(self, input_data: dict, dry_run: bool = True) -> dict:
        """Add models to appropriate provider files."""
        results = {
            'added': [],
            'updated': [],
            'skipped': [],
            'errors': [],
            'missing_benchmarks': []
        }

        provider = input_data.get('provider')
        target_file = input_data.get('target_file')  # Optional: specify exact file
        models_to_add = input_data.get('models', [])

        if not provider and not target_file:
            results['errors'].append("Must specify either 'provider' or 'target_file'")
            return results

        # Determine target file
        if target_file:
            file_path = self.data_dir / target_file
        else:
            # Default to models/{provider}.json
            file_path = self.models_dir / f'{provider.lower()}.json'

        if not file_path.exists():
            results['errors'].append(f"Target file not found: {file_path}")
            return results

        # Load existing file
        with open(file_path) as f:
            existing_data = json.load(f)

        existing_model_ids = {m['id'] for m in existing_data.get('models', [])}

        for model in models_to_add:
            model_id = model['id']

            # Validate benchmark references
            benchmark_ids = set(model.get('benchmarks', {}).keys())
            valid, missing = self.validate_benchmarks_exist(benchmark_ids)
            if not valid:
                results['missing_benchmarks'].extend(
                    [f"{model_id}: {b}" for b in missing]
                )

            # Check if model exists
            if model_id in existing_model_ids:
                # Find and compare
                existing_model = next(m for m in existing_data['models'] if m['id'] == model_id)
                if existing_model == model:
                    results['skipped'].append(f"{model_id} (identical)")
                else:
                    results['updated'].append(f"{model_id} (data differs)")
                    if not dry_run:
                        self._update_model_in_file(file_path, existing_data, model_id, model)
            else:
                results['added'].append(model_id)
                if not dry_run:
                    self._add_model_to_file(file_path, existing_data, model)

        return results

    def _add_model_to_file(self, file_path: Path, data: dict, model: dict):
        """Add a model to a file."""
        data['models'].append(model)
        data['last_updated'] = datetime.now().isoformat()

        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

    def _update_model_in_file(self, file_path: Path, data: dict, model_id: str, new_model: dict):
        """Update an existing model in a file by merging fields."""
        for i, model in enumerate(data['models']):
            if model['id'] == model_id:
                # Merge new fields into existing model instead of replacing
                data['models'][i].update(new_model)
                break

        data['last_updated'] = datetime.now().isoformat()

        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

    def validate_all(self) -> dict:
        """Validate entire dataset for consistency."""
        results = {
            'valid': True,
            'errors': [],
            'warnings': []
        }

        # Load all data
        all_benchmarks = self.load_all_benchmarks()
        all_models = self.load_all_models()

        # Check for duplicate benchmark IDs across categories
        benchmark_counts = {}
        for category_file in self.benchmarks_dir.glob('*.json'):
            if category_file.name == 'categories.json':
                continue
            with open(category_file) as f:
                data = json.load(f)
                for bench_id in data.get('benchmarks', {}).keys():
                    benchmark_counts[bench_id] = benchmark_counts.get(bench_id, 0) + 1

        duplicates = [bid for bid, count in benchmark_counts.items() if count > 1]
        if duplicates:
            results['valid'] = False
            results['errors'].append(f"Duplicate benchmark IDs: {duplicates}")

        # Check for duplicate model IDs
        all_model_ids = []
        for file_data in all_models.values():
            all_model_ids.extend([m['id'] for m in file_data.get('models', [])])

        duplicate_models = [mid for mid in set(all_model_ids) if all_model_ids.count(mid) > 1]
        if duplicate_models:
            results['valid'] = False
            results['errors'].append(f"Duplicate model IDs: {duplicate_models}")

        # Check all model benchmark references
        for file_path, file_data in all_models.items():
            for model in file_data.get('models', []):
                for bench_id in model.get('benchmarks', {}).keys():
                    if bench_id not in all_benchmarks:
                        results['warnings'].append(
                            f"{model['id']} references unknown benchmark: {bench_id}"
                        )

        return results


def print_results(results: dict, operation: str):
    """Pretty print operation results."""
    print(f"\n{'='*60}")
    print(f"Results: {operation}")
    print('='*60)

    if results.get('added'):
        print(f"\n✅ Added ({len(results['added'])}):")
        for item in results['added']:
            print(f"  + {item}")

    if results.get('updated'):
        print(f"\n🔄 Updated ({len(results['updated'])}):")
        for item in results['updated']:
            print(f"  ~ {item}")

    if results.get('skipped'):
        print(f"\n⏭️  Skipped ({len(results['skipped'])}):")
        for item in results['skipped']:
            print(f"  = {item}")

    if results.get('missing_benchmarks'):
        print(f"\n⚠️  Missing benchmark references ({len(results['missing_benchmarks'])}):")
        for item in results['missing_benchmarks']:
            print(f"  ! {item}")

    if results.get('errors'):
        print(f"\n❌ Errors ({len(results['errors'])}):")
        for error in results['errors']:
            print(f"  ✗ {error}")

    if results.get('warnings'):
        print(f"\n⚠️  Warnings ({len(results['warnings'])}):")
        for warning in results['warnings']:
            print(f"  ! {warning}")

    print()


def main():
    parser = argparse.ArgumentParser(
        description='Manage LLM Pareto dataset: add models and benchmarks with validation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Add benchmarks (dry run)
  python manage_data.py add-benchmarks benchmarks.json --dry-run

  # Add benchmarks (apply changes)
  python manage_data.py add-benchmarks benchmarks.json

  # Add models (dry run)
  python manage_data.py add-models /tmp/models.json --dry-run

  # Add models (apply changes)
  python manage_data.py add-models /tmp/models.json

  # Validate entire dataset
  python manage_data.py validate

Input file format examples in CLAUDE.md
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Add benchmarks command
    bench_parser = subparsers.add_parser('add-benchmarks', help='Add benchmarks to dataset')
    bench_parser.add_argument('input_file', help='JSON file with benchmarks to add')
    bench_parser.add_argument('--dry-run', action='store_true',
                             help='Preview changes without applying')

    # Add models command
    models_parser = subparsers.add_parser('add-models', help='Add models to dataset')
    models_parser.add_argument('input_file', help='JSON file with models to add')
    models_parser.add_argument('--dry-run', action='store_true',
                              help='Preview changes without applying')

    # Validate command
    subparsers.add_parser('validate', help='Validate entire dataset')

    # Query command
    query_parser = subparsers.add_parser('query', help='Query a specific model by ID')
    query_parser.add_argument('model_id', help='Model ID to query')

    # List command
    list_parser = subparsers.add_parser('list', help='List all models')
    list_parser.add_argument('--provider', help='Filter by provider')
    list_parser.add_argument('--family', help='Filter by family')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Initialize manager
    data_dir = Path(__file__).parent / 'data'
    manager = DataManager(data_dir)

    # Execute command
    if args.command == 'add-benchmarks':
        with open(args.input_file) as f:
            input_data = json.load(f)

        if args.dry_run:
            print("\n🔍 DRY RUN MODE - No changes will be applied\n")

        results = manager.add_benchmarks(input_data, dry_run=args.dry_run)
        print_results(results, f"Add Benchmarks ({'DRY RUN' if args.dry_run else 'APPLIED'})")

        if args.dry_run and (results['added'] or results['updated']):
            print("💡 Run without --dry-run to apply these changes\n")

    elif args.command == 'add-models':
        with open(args.input_file) as f:
            input_data = json.load(f)

        if args.dry_run:
            print("\n🔍 DRY RUN MODE - No changes will be applied\n")

        results = manager.add_models(input_data, dry_run=args.dry_run)
        print_results(results, f"Add Models ({'DRY RUN' if args.dry_run else 'APPLIED'})")

        if results['missing_benchmarks']:
            print("⚠️  Some benchmarks don't exist yet. Add them first with add-benchmarks\n")

        if args.dry_run and (results['added'] or results['updated']):
            print("💡 Run without --dry-run to apply these changes\n")

    elif args.command == 'validate':
        results = manager.validate_all()

        print(f"\n{'='*60}")
        print("Dataset Validation")
        print('='*60)

        if results['valid'] and not results['warnings']:
            print("\n✅ Dataset is valid!\n")
        elif results['valid'] and results['warnings']:
            print("\n✅ Dataset is valid (with warnings)\n")
            print_results(results, "Validation")
        else:
            print("\n❌ Dataset has errors\n")
            print_results(results, "Validation")
            sys.exit(1)

    elif args.command == 'query':
        result = manager.query_model(args.model_id)

        if not result:
            print(f"\n❌ Model '{args.model_id}' not found\n")
            sys.exit(1)

        print(f"\n{'='*60}")
        print(f"Model: {result['model'].get('name', result['model']['id'])}")
        print('='*60)
        print(f"\nID: {result['model']['id']}")
        print(f"Provider: {result['provider']}")
        print(f"Family: {result['model'].get('family', 'N/A')}")
        print(f"File: {result['file']}")

        if result['model'].get('parameters_billions'):
            print(f"\nTotal Parameters: {result['model']['parameters_billions']}B")
        if result['model'].get('active_parameters_billions'):
            print(f"Active Parameters: {result['model']['active_parameters_billions']}B")

        if result['model'].get('parameters_source'):
            src = result['model']['parameters_source']
            print(f"\nParameter Source:")
            print(f"  Type: {src.get('type', 'N/A')}")
            print(f"  URL: {src.get('url', 'N/A')}")
            if src.get('notes'):
                print(f"  Notes: {src['notes']}")

        if result['model'].get('pricing'):
            pricing = result['model']['pricing']
            print(f"\nPricing:")
            print(f"  Input: ${pricing['input_per_1m_tokens']:.2f} per 1M tokens")
            print(f"  Output: ${pricing['output_per_1m_tokens']:.2f} per 1M tokens")

        if result['model'].get('benchmarks'):
            print(f"\nBenchmarks ({len(result['model']['benchmarks'])}):")
            for bench_id, bench_data in sorted(result['model']['benchmarks'].items()):
                print(f"  {bench_id}: {bench_data.get('score', 'N/A')}")

        print()

    elif args.command == 'list':
        models = manager.list_models(
            provider=args.provider,
            family=args.family
        )

        if not models:
            print("\n❌ No models found matching criteria\n")
            sys.exit(1)

        print(f"\n{'='*60}")
        print(f"Models ({len(models)})")
        print('='*60)
        print()

        # Group by provider
        current_provider = None
        for model in models:
            if model['provider'] != current_provider:
                current_provider = model['provider']
                print(f"\n{current_provider}:")

            params_str = ""
            if model['active_parameters_billions'] and model['parameters_billions']:
                params_str = f" ({model['active_parameters_billions']}B / {model['parameters_billions']}B)"
            elif model['parameters_billions']:
                params_str = f" ({model['parameters_billions']}B)"

            print(f"  {model['id']}: {model['name']}{params_str}")

        print()


if __name__ == '__main__':
    main()
