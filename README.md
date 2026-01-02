# LLM Pareto Frontier Explorer

An interactive visualization tool for comparing Large Language Models across multiple benchmarks, parameter counts, and costs using Pareto frontier analysis.

## Overview

This project visualizes LLM performance trade-offs by plotting benchmark scores against:
- Number of parameters (billions)
- Cost per million tokens (input/output average)

The Pareto frontier highlights the most efficient models—those that achieve the best performance for a given parameter count or cost.

## Features

- **Interactive Scatter Plots**: Chart.js-powered visualizations with zoom and pan
- **Multiple Benchmarks**: MMLU, HumanEval, Chatbot Arena, GSM8K, BBH, and more
- **Pareto Frontier**: Automatically calculated efficient frontier
- **Citation Tracking**: Every data point includes source URL, type, and collection date
- **Responsive Design**: Works on desktop and mobile devices
- **Zero Build Step**: Pure HTML/CSS/JS—no build tools required

## Project Structure

```
llm-pareto/
├── index.html              # Main page
├── css/styles.css          # Styling
├── js/app.js               # Application logic
├── data/
│   ├── manifest.json       # List of all model files
│   ├── benchmarks/         # Benchmark definitions by category
│   │   ├── categories.json
│   │   ├── knowledge.json
│   │   ├── coding.json
│   │   ├── math.json
│   │   └── agentic.json
│   └── models/             # Model data organized by provider
│       ├── google.json
│       ├── meta.json
│       ├── openai/         # OpenAI models split by generation
│       ├── anthropic/      # Anthropic models split by generation
│       └── qwen/           # Qwen models
├── manage_data.py          # Data management script
├── CLAUDE.md               # Instructions for AI assistant
└── README.md               # This file
```

## Data Schema

Each model in the provider files under `data/models/` includes:
- **Metadata**: Name, provider, family, parameter count
- **Benchmarks**: Scores with citations (URL, type, collection date)
- **Pricing**: Input/output costs with source
- **Citations**: Every field has source tracking

Example:
```json
{
  "id": "gpt-4o",
  "name": "GPT-4o",
  "parameters_billions": 1760,
  "parameters_source": {
    "url": "https://openai.com/...",
    "type": "primary",
    "collected": "2024-05-13"
  },
  "benchmarks": {
    "mmlu": {
      "score": 88.7,
      "source": {...}
    }
  }
}
```

## Usage

### View the Site Locally

1. Clone the repository
2. Serve with any HTTP server:
   ```bash
   cd llm-pareto
   python3 -m http.server 8000
   ```
3. Open http://localhost:8000

### GitHub Pages Deployment

1. Push to GitHub
2. Enable GitHub Pages in Settings → Pages
3. Set source to `main` branch
4. Site will be live at `https://username.github.io/llm-pareto`

### Update Data

Use the `manage_data.py` script to add benchmarks and models with validation:

```bash
# Add benchmarks (dry-run first to preview)
python manage_data.py add-benchmarks benchmarks.json --dry-run
python manage_data.py add-benchmarks benchmarks.json

# Add models (dry-run first to preview)
python manage_data.py add-models /tmp/models.json --dry-run
python manage_data.py add-models /tmp/models.json

# Validate entire dataset
python manage_data.py validate

# See --help for options
python manage_data.py --help
```

For detailed input formats and examples, see `CLAUDE.md`.

## Data Sources

- **LMSYS Chatbot Arena**: https://lmarena.ai/leaderboard
- **Hugging Face Leaderboard**: https://huggingface.co/spaces/open-llm-leaderboard
- **Provider Pricing**: OpenAI, Anthropic, Google documentation
- **Model Papers**: arXiv, provider blogs, research publications

## Contributing

Contributions welcome! Please ensure:
1. All data points include citations with URLs and dates
2. Prefer primary sources (provider blogs, papers) over aggregators
3. Validate against official leaderboards before submitting
4. Update `last_updated` timestamp in the provider file you touched

## License

MIT License

## Citation

If you use this data or visualization in research, please cite the original benchmark sources listed in the data files.
