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
├── js/app.js               # All frontend logic
├── data/
│   ├── models.json         # Model data with citations
│   └── sources.json        # Source configurations for automation
└── scripts/                # Data collection (not deployed)
    ├── collect_data.py     # Main orchestrator
    ├── llm_parser.py       # LLM-based parsing
    ├── validate.py         # Data quality checks
    └── scrapers/           # Individual scrapers
```

## Data Schema

Each model in `data/models.json` includes:
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

#### Manual Updates
Edit `data/models.json` directly in GitHub or locally, then commit and push.

#### Automated Updates (Local)
Run the Python scripts weekly via systemd:

```bash
# Set up systemd timer (see scripts/README.md)
systemctl --user enable llm-pareto-update.timer
systemctl --user start llm-pareto-update.timer
```

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
4. Update `last_updated` timestamp in `models.json`

## License

MIT License

## Citation

If you use this data or visualization in research, please cite the original benchmark sources listed in the data files.
