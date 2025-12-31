# LLM Pareto Data Collection Scripts

Automated scrapers for collecting LLM pricing and benchmark data.

## Quick Start

### Test Pricing Scraper (Dry Run)

```bash
cd /home/sean/sandbox/llm-pareto
python3 scripts/collect_data.py --dry-run
```

This will:
- Scrape pricing from OpenAI, Anthropic, Google
- Use Claude CLI to parse HTML
- Show what would change
- **NOT modify** `data/models.json`

### Update Data For Real

```bash
python3 scripts/collect_data.py
```

This actually updates `data/models.json` with new pricing.

## Architecture

```
scripts/
├── collect_data.py          # Main orchestrator
├── llm_parser.py            # Claude CLI wrapper
└── scrapers/
    ├── base.py              # Base classes
    └── pricing.py           # Pricing scrapers
```

## How It Works

1. **Fetch**: Download HTML from provider pricing pages
2. **Parse**: Use Claude CLI to extract structured JSON
3. **Validate**: Check prices are in reasonable ranges
4. **Merge**: Update existing models or add new ones
5. **Save**: Write to `data/models.json` (if not dry-run)

## Individual Component Testing

### Test LLM Parser

```bash
python3 scripts/llm_parser.py
```

### Test Pricing Scraper Only

```bash
python3 scripts/scrapers/pricing.py
```

## Requirements

- Python 3.7+
- `requests` library: `pip install requests`
- `claude` CLI tool (Claude Code)

## Adding New Scrapers

See `scrapers/pricing.py` for examples. Pattern:

```python
class MyScraper(BaseScraper):
    def scrape_provider(self):
        html = self.fetch_url(url)
        prompt = create_pricing_prompt(html, "Provider")
        data = self.parser.parse(prompt)
        return {"models": data, "source": {...}}
```

## Troubleshooting

**Claude CLI not found:**
- Make sure `claude` command is in PATH
- Test with: `echo "hello" | claude`

**JSON parsing fails:**
- Claude response might not be valid JSON
- Check `llm_parser.py` extraction logic
- Try adding examples to prompt

**HTTP errors:**
- Provider website might be down
- Check URL is still valid
- Increase timeout in `BaseScraper.__init__`
