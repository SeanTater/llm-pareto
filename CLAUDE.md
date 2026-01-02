# Instructions for Claude Code

## ⚠️ Important: Use the Data Management Script

When adding models or benchmarks to this project, **always use `manage_data.py`** instead of manually editing JSON files. This prevents errors, detects conflicts, and handles large files gracefully.

## Quick Reference

```bash
# ALWAYS start with dry-run to preview changes
python manage_data.py add-benchmarks /tmp/benchmarks.json --dry-run
python manage_data.py add-models /tmp/models.json --dry-run

# Then apply if everything looks good
python manage_data.py add-benchmarks /tmp/benchmarks.json
python manage_data.py add-models /tmp/models.json

# Validate dataset after changes
python manage_data.py validate
```

## Input File Formats

### Adding Benchmarks

Create a temporary JSON file with new benchmarks:

```json
{
  "benchmarks": {
    "benchmark_id": {
      "name": "Short Name",
      "full_name": "Full Benchmark Name",
      "description": "What this benchmark tests (1-2 sentences)",
      "category": "knowledge|coding|math|agentic",
      "scale": "0-100%",
      "higher_is_better": true
    }
  }
}
```

**Example:**
```bash
cat > /tmp/new_benchmarks.json <<'EOF'
{
  "benchmarks": {
    "hle_with_tools": {
      "name": "HLE (with tools)",
      "full_name": "Humanity's Last Exam with Search and Code",
      "description": "Academic reasoning benchmark with access to search and code execution tools",
      "category": "knowledge",
      "scale": "0-100%",
      "higher_is_better": true
    },
    "global_piqa": {
      "name": "Global PIQA",
      "full_name": "Global Physical Interaction QA",
      "description": "Commonsense reasoning across 100 languages and cultures",
      "category": "knowledge",
      "scale": "0-100%",
      "higher_is_better": true
    }
  }
}
EOF

python manage_data.py add-benchmarks /tmp/new_benchmarks.json --dry-run
```

### Adding Models

Create a temporary JSON file with new models:

```json
{
  "provider": "ProviderName",
  "target_file": "models/provider/specific_file.json",
  "models": [
    {
      "id": "model-id-kebab-case",
      "name": "Human Readable Name",
      "provider": "ProviderName",
      "family": "ModelFamily",
      "parameters_billions": 200,
      "parameters_source": {
        "url": "https://source.url",
        "type": "estimated|official",
        "collected": "2025-12-31",
        "notes": "Optional notes"
      },
      "pricing": {
        "input_per_1m_tokens": 0.50,
        "output_per_1m_tokens": 3.00,
        "source": {
          "url": "https://pricing.url",
          "type": "primary",
          "collected": "2025-12-31"
        }
      },
      "benchmarks": {
        "benchmark_id": {
          "score": 85.5,
          "source": {
            "url": "https://source.url",
            "type": "primary|secondary",
            "collected": "2025-12-31",
            "notes": "Optional notes"
          }
        }
      }
    }
  ]
}
```

**Notes:**
- `target_file` is optional - defaults to `models/{provider}.json`
- Use `target_file` for provider subdirectories: `models/openai/gpt_5_2.json`
- `parameters_billions` and `parameters_source` are optional
- `pricing` is optional

**Example:**
```bash
cat > /tmp/gemini3.json <<'EOF'
{
  "provider": "Google",
  "target_file": "models/google.json",
  "models": [
    {
      "id": "gemini-3-flash-thinking",
      "name": "Gemini 3 Flash Thinking",
      "provider": "Google",
      "family": "Gemini",
      "parameters_billions": 200,
      "parameters_source": {
        "url": "https://deepmind.google/models/gemini/",
        "type": "estimated",
        "collected": "2025-12-31",
        "notes": "Ballpark estimate"
      },
      "pricing": {
        "input_per_1m_tokens": 0.50,
        "output_per_1m_tokens": 3.00,
        "source": {
          "url": "https://deepmind.google/models/gemini/",
          "type": "primary",
          "collected": "2025-12-31"
        }
      },
      "benchmarks": {
        "hle": {
          "score": 33.7,
          "source": {
            "url": "https://deepmind.google/models/gemini/",
            "type": "primary",
            "collected": "2025-12-31",
            "notes": "No tools"
          }
        },
        "gpqa_diamond": {
          "score": 90.4,
          "source": {
            "url": "https://deepmind.google/models/gemini/",
            "type": "primary",
            "collected": "2025-12-31",
            "notes": "No tools"
          }
        }
      }
    }
  ]
}
EOF

python manage_data.py add-models /tmp/gemini3.json --dry-run
```

## Workflow for Adding Models from Tables

When the user provides a benchmark comparison table:

1. **Identify new benchmarks** - Check which benchmarks don't exist yet
2. **Add benchmarks first** - Create benchmarks.json with new ones
3. **Add models** - Create `/tmp/models.json` with the data
4. **Always dry-run first** - Review what will change
5. **Apply if good** - Run without --dry-run
6. **Validate** - Run validate command

**Example workflow:**
```bash
# Step 1: Add new benchmarks
cat > /tmp/benchmarks.json <<'EOF'
{
  "benchmarks": {
    "new_benchmark_id": {...}
  }
}
EOF
python manage_data.py add-benchmarks /tmp/benchmarks.json --dry-run
python manage_data.py add-benchmarks /tmp/benchmarks.json

# Step 2: Add models
cat > /tmp/models.json <<'EOF'
{
  "provider": "Google",
  "models": [...]
}
EOF
python manage_data.py add-models /tmp/models.json --dry-run
python manage_data.py add-models /tmp/models.json

# Step 3: Validate
python manage_data.py validate
```

## Common Benchmark IDs

Quick reference for existing benchmarks (check with validate if unsure):

**Knowledge:**
- mmlu, mmmlu, mmmu, mmmu_pro
- gpqa, gpqa_diamond
- arenahard, livebench
- arc_agi_1, arc_agi_2
- hle (Humanity's Last Exam)

**Coding:**
- humaneval, livecodebench, livecodebench_pro
- codeforces, aider, bfcl

**Math:**
- aime, aime2025, aime2025_no_tools, aime24, aime25
- gsm8k, frontiermath_tier1_3, frontiermath_tier4
- hmmt_feb_2025

**Agentic:**
- swebench_verified, swebench_pro_public
- terminalbench, terminalbench_2_0
- osworld, tau2bench, tau2bench_retail, tau2bench_airline, tau2bench_telecom
- finance_agent, multiif, toolathlon
- scale_mcp_atlas, screenspot_pro
- vending_bench_2

## Tips

- **Use descriptive IDs**: `model-name-version` in kebab-case
- **Source URLs**: Use the most authoritative source (model card, official blog post)
- **Notes field**: Clarify test conditions (e.g., "No tools", "With code execution")
- **Check for duplicates**: Script will warn but won't prevent adding
- **Dry-run everything**: Always preview before applying

## Troubleshooting

**Missing benchmarks error:**
```
⚠️  Missing benchmark references:
  ! model-id: unknown_benchmark
```
→ Add the benchmark first with `add-benchmarks`

**Duplicate model ID:**
```
❌ Errors:
  ✗ Duplicate model IDs: ['model-id']
```
→ Model already exists, will be updated (check dry-run output)

**File not found:**
```
❌ Errors:
  ✗ Target file not found: data/models/newprovider.json
```
→ Create the file first or use correct `target_file` path
