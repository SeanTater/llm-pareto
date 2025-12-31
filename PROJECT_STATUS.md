# LLM Pareto Frontier - Project Status
**Last Updated: 2025-12-31**

## 🎯 Current State

### ✅ What's Working
- **Live Site**: https://seantater.github.io/llm-pareto/
- **16 models** with 2025 pricing data
- **Brand color-coded scatter plot** (OpenAI green, Anthropic orange, Google blue, Meta blue, xAI black)
- **Model detail cards** showing parameters, benchmarks, separate input/output pricing
- **Responsive design** for mobile/desktop
- **Ollama integration** working on localhost:11437 with ministral-3:latest (GPU proxy)

### 🔧 What's Built But Needs Tuning
- **Python scraping infrastructure** (`scripts/` directory)
  - LLM parser with Ollama + Claude CLI backends
  - Pricing scrapers for OpenAI, Anthropic, Google
  - Base classes, error handling, dry-run mode
- **Anti-Anthropic blocks bypassed** - switching to Ollama fixed getting blocked
- **OpenAI still blocks everyone** (403 Forbidden) - need manual entry or different approach

### ⚠️ Current Issue: Mistral Prompt Following
**Problem**: Ministral-3 is describing content instead of extracting JSON
- Anthropic scrape: Returns "It looks like you've shared CSS..."
- Google scrape: Returns "The page appears to be Gemini pricing..."
- **Just improved prompts** - need to test if it works now

## 📂 Project Structure

```
llm-pareto/
├── index.html              # Main page
├── css/styles.css          # Styling with model cards
├── js/app.js               # Chart.js, Pareto calc, filters, color coding
├── data/
│   ├── models.json         # 16 models with pricing + citations
│   └── sources.json        # Source configs for automation
└── scripts/                # Data collection (NOT deployed)
    ├── collect_data.py     # Main orchestrator
    ├── llm_parser.py       # Ollama/Claude wrapper
    └── scrapers/
        ├── base.py
        └── pricing.py      # OpenAI/Anthropic/Google scrapers
```

## 🚀 How To Use

### Test Scraper (Dry Run)
```bash
cd /home/sean/sandbox/llm-pareto
python3 scripts/collect_data.py --dry-run
```

### Test LLM Parser
```bash
python3 scripts/llm_parser.py
```

### Update Models Data
```bash
python3 scripts/collect_data.py  # Actually updates models.json
git add data/models.json
git commit -m "Update pricing data"
git push
```

## 🔑 Key Configuration

### Ollama Setup
- **Endpoint**: http://localhost:11437
- **Model**: ministral-3:latest (8B params, Q4_K_M)
- **Backend**: GPU proxy (set up by user)
- **Alternative models available**:
  - ministral-3:14b (larger, slower)
  - ministral-3:3b (smaller, faster)
  - qwen3-vl:8b (vision capable, very slow on CPU)

### LLM Parser Backends
```python
# Use Ollama (default)
parser = LLMParser(
    model="ministral-3:latest",
    backend="ollama",
    ollama_url="http://localhost:11437"
)

# Or fallback to Claude CLI
parser = LLMParser(model="sonnet", backend="claude")
```

## 📊 Current Data

### Models (16 total)
**OpenAI (6)**: GPT-5.2, GPT-5.2 Pro, GPT-5 mini, GPT-4.1, GPT-4.1 mini, GPT-4o
**Anthropic (6)**: Claude Opus 4.5, Sonnet 4.5, 3.7 Sonnet, 3.5 Sonnet, Haiku 4, 3.5 Haiku
**Google (1)**: Gemini 2.0 Flash
**Meta (2)**: Llama 3.1 70B, Llama 3.1 405B
**OpenAI (1)**: GPT-3.5 Turbo

### What's Missing
- **Benchmark data** for most 2025 models (MMLU, HumanEval, etc.)
- **Parameter counts** for most models
- **More providers**: xAI/Grok, Mistral, DeepSeek, Qwen

## 🎯 Next Steps (In Order)

### 1. Fix Mistral Extraction (URGENT)
**Status**: Just improved prompts - need to test
```bash
python3 scripts/scrapers/pricing.py  # Test if new prompts work
```

**If still failing**: Try:
- Add few-shot examples to prompt
- Use structured output format in Ollama API
- Switch to ministral-3:14b (smarter but slower)
- Fall back to Claude CLI for critical scrapers

### 2. Add Benchmark Data
**Approach**: Scrape from HuggingFace model cards or leaderboards
- LMSYS Chatbot Arena for human preference
- Hugging Face Open LLM Leaderboard for academic benchmarks
- Could use HuggingFace API instead of scraping

### 3. Expand Model Coverage
**Priority models to add**:
- xAI Grok 2, Grok 2 mini
- Mistral Large 2, Small
- DeepSeek V3
- Qwen 2.5 series
- More Gemini variants

### 4. Improve Visualization
- Add benchmark score labels on chart points
- Filter by price range
- Show Pareto frontier for multiple objectives (3D plot?)
- Export chart as PNG

### 5. Automation
- Set up systemd timer for weekly scraping
- Auto-commit and push updates
- Email/notification on scrape failures
- Data validation dashboard

## 🐛 Known Issues

1. **OpenAI blocks all scrapers** (403) - need manual data entry
2. **Mistral not extracting JSON reliably** - prompt engineering needed
3. **No benchmark data yet** - all models show pricing only
4. **Old 2024 models mixed with 2025** - need to clean up or archive
5. **Missing parameter counts** for many models

## 💡 Design Decisions Made

- **Ollama over Claude CLI**: Avoid anti-Anthropic blocks
- **Manual OpenAI entry**: 403 blocking is hard to bypass
- **JSON over YAML**: Better browser compatibility
- **Separate input/output pricing**: User requested (not averaged)
- **Brand colors**: OpenAI green, Anthropic orange, Google blue, Meta blue
- **No chart legend**: Too crowded - using data cards instead
- **Dry-run mode**: Safety for testing scrapers

## 📝 Commits Made Today

1. Initial setup - basic frontend with 6 old models
2. Color coding + model detail cards
3. Pricing scrapers + Ollama integration + 10 new 2025 models

## 🔗 Important URLs

- **Live Site**: https://seantater.github.io/llm-pareto/
- **Repo**: https://github.com/SeanTater/llm-pareto
- **Ollama Docs**: https://github.com/ollama/ollama/blob/main/docs/api.md

## 📞 When Resuming

**First check**: Did Mistral prompt improvements work?
```bash
python3 scripts/scrapers/pricing.py  # Should extract JSON now
```

**If yes**: Run full scraper and add benchmark scrapers
**If no**: Need to try few-shot prompting or switch models
