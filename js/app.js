// Global state
let modelsData = null;
let benchmarksData = null;
let chart = null;
let currentBenchmark = 'mmmlu';
let currentXAxis = 'cost';
let currentFamily = 'all';
const showPareto = true;  // Always enabled
const showCitations = true;  // Always enabled

// Cost estimation constants ($ per 1M tokens per billion parameters)
// Calibrated from OpenRouter pricing for DeepSeek-R1:
// input $0.300 / 1M, output $1.200 / 1M, active 37B, total 671B.
const COST_PER_BILLION_PARAMS_ACTIVE = {
    input: 0.300 / 37,   // ~$0.00811 per 1M tokens per billion active params
    output: 1.200 / 37   // ~$0.03243 per 1M tokens per billion active params
};
const COST_PER_BILLION_PARAMS_TOTAL = {
    input: 0.300 / 671,  // ~$0.00045 per 1M tokens per billion total params
    output: 1.200 / 671  // ~$0.00179 per 1M tokens per billion total params
};

// Brand colors for providers
const PROVIDER_COLORS = {
    'OpenAI': { bg: 'rgba(16, 163, 127, 0.7)', border: 'rgba(16, 163, 127, 1)' },      // OpenAI green
    'Anthropic': { bg: 'rgba(204, 85, 51, 0.7)', border: 'rgba(204, 85, 51, 1)' },     // Anthropic orange
    'Google': { bg: 'rgba(66, 133, 244, 0.7)', border: 'rgba(66, 133, 244, 1)' },      // Google blue
    'Meta': { bg: 'rgba(0, 102, 255, 0.7)', border: 'rgba(0, 102, 255, 1)' },          // Meta blue
    'Qwen': { bg: 'rgba(124, 58, 237, 0.7)', border: 'rgba(124, 58, 237, 1)' },        // Qwen purple
    'xAI': { bg: 'rgba(0, 0, 0, 0.7)', border: 'rgba(0, 0, 0, 1)' },                   // xAI black
    'Mistral': { bg: 'rgba(255, 122, 0, 0.7)', border: 'rgba(255, 122, 0, 1)' },       // Mistral orange
    'DeepSeek': { bg: 'rgba(59, 130, 246, 0.7)', border: 'rgba(59, 130, 246, 1)' },    // DeepSeek blue
    'Moonshot': { bg: 'rgba(236, 72, 153, 0.7)', border: 'rgba(236, 72, 153, 1)' },    // Moonshot pink
    'MiniMax': { bg: 'rgba(245, 158, 11, 0.7)', border: 'rgba(245, 158, 11, 1)' },     // MiniMax amber
    'Zhipu': { bg: 'rgba(34, 197, 94, 0.7)', border: 'rgba(34, 197, 94, 1)' },         // Zhipu green
    'default': { bg: 'rgba(107, 114, 128, 0.7)', border: 'rgba(107, 114, 128, 1)' }    // Gray fallback
};

// Get color for a provider
function getProviderColor(provider) {
    return PROVIDER_COLORS[provider] || PROVIDER_COLORS['default'];
}

// Estimate cost based on parameter count (uses active params if available, else total)
function estimateCost(model) {
    if (model.active_parameters_billions) {
        const params = model.active_parameters_billions;
        return {
            input_per_1m_tokens: params * COST_PER_BILLION_PARAMS_ACTIVE.input,
            output_per_1m_tokens: params * COST_PER_BILLION_PARAMS_ACTIVE.output,
            is_estimated: true
        };
    }
    if (model.parameters_billions) {
        const params = model.parameters_billions;
        return {
            input_per_1m_tokens: params * COST_PER_BILLION_PARAMS_TOTAL.input,
            output_per_1m_tokens: params * COST_PER_BILLION_PARAMS_TOTAL.output,
            is_estimated: true
        };
    }
    return null;
}

// Estimate parameters based on pricing (reverse calculation)
function estimateParameters(model) {
    if (!model.pricing) return null;

    // Use average of input and output estimates
    const inputEstimate = model.pricing.input_per_1m_tokens / COST_PER_BILLION_PARAMS_TOTAL.input;
    const outputEstimate = model.pricing.output_per_1m_tokens / COST_PER_BILLION_PARAMS_TOTAL.output;

    return {
        parameters_billions: (inputEstimate + outputEstimate) / 2,
        is_estimated: true
    };
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', async () => {
    await loadData();
    initControls();
    renderChart();
    renderDataTable();
});

// Load data from JSON files
async function loadData() {
    try {
        // Load benchmark category files in parallel
        const benchmarkCategories = ['knowledge', 'coding', 'math', 'agentic'];
        const benchmarkPromises = benchmarkCategories.map(category =>
            fetch(`data/benchmarks/${category}.json`).then(res => res.json())
        );
        const categoriesPromise = fetch('data/benchmarks/categories.json').then(res => res.json());

        const [categoryFiles, categoriesData] = await Promise.all([
            Promise.all(benchmarkPromises),
            categoriesPromise
        ]);

        // Merge all benchmark category files into one object
        const allBenchmarks = {};
        categoryFiles.forEach(file => {
            Object.assign(allBenchmarks, file.benchmarks);
        });

        // Create combined benchmarks data structure
        benchmarksData = {
            benchmarks: allBenchmarks,
            categories: categoriesData.categories
        };

        console.log(`Loaded ${Object.keys(allBenchmarks).length} benchmarks from ${categoryFiles.length} category files`);

        // Load manifest to get list of model files
        const manifestResponse = await fetch('data/manifest.json');
        const manifest = await manifestResponse.json();

        // Load all model files in parallel
        const modelFilesPromises = manifest.model_files.map(file =>
            fetch(`data/${file}`).then(res => res.json())
        );
        const modelFiles = await Promise.all(modelFilesPromises);

        // Combine all models from all files
        const allModels = modelFiles.flatMap(file => file.models);

        // Create combined data structure (compatible with existing code)
        modelsData = {
            models: allModels,
            last_updated: manifest.last_updated
        };

        console.log(`Loaded ${allModels.length} models from ${manifest.model_files.length} provider files`);

        // Update last updated timestamp
        if (modelsData.last_updated) {
            const date = new Date(modelsData.last_updated);
            document.getElementById('last-updated').textContent =
                `Last Updated: ${date.toLocaleDateString()}`;
        }

        // Populate benchmark dropdown after data loads
        populateBenchmarkDropdown();
    } catch (error) {
        console.error('Error loading data:', error);
        document.getElementById('last-updated').textContent =
            'Error loading data. Please check console.';
    }
}

// Initialize control event listeners
function initControls() {
    document.getElementById('benchmark-select').addEventListener('change', (e) => {
        currentBenchmark = e.target.value;
        updateBenchmarkInfo(currentBenchmark);
        renderChart();
        renderDataTable();
    });

    document.getElementById('xaxis-select').addEventListener('change', (e) => {
        currentXAxis = e.target.value;
        renderChart();
        renderDataTable();
    });

    document.getElementById('family-filter').addEventListener('change', (e) => {
        currentFamily = e.target.value;
        renderChart();
        renderDataTable();
    });
}

// Count how many models have data for each benchmark AND can be plotted
function countModelsForBenchmark(benchmarkId) {
    return modelsData.models.filter(model => {
        // Must have benchmark data
        if (!model.benchmarks || !model.benchmarks[benchmarkId]) {
            return false;
        }

        // Must have at least one valid x-axis value to be plottable
        const hasActiveParams = model.active_parameters_billions || model.parameters_billions;
        const hasPricing = model.pricing &&
            model.pricing.input_per_1m_tokens !== undefined &&
            model.pricing.output_per_1m_tokens !== undefined;
        const hasEstimatedCost = estimateCost(model) !== null;

        return hasActiveParams || hasPricing || hasEstimatedCost;
    }).length;
}

// Dynamically populate benchmark dropdown with categories
function populateBenchmarkDropdown() {
    const select = document.getElementById('benchmark-select');
    select.innerHTML = ''; // Clear existing options

    // Get all benchmarks that exist in actual data
    const benchmarksInData = new Set();
    modelsData.models.forEach(model => {
        Object.keys(model.benchmarks || {}).forEach(b => benchmarksInData.add(b));
    });

    // Group benchmarks by category
    const categorized = {};
    benchmarksInData.forEach(benchmarkId => {
        const meta = benchmarksData.benchmarks[benchmarkId];
        if (!meta) return; // Skip if no metadata

        const category = meta.category || 'other';
        if (!categorized[category]) categorized[category] = [];
        categorized[category].push({
            id: benchmarkId,
            meta: meta,
            count: countModelsForBenchmark(benchmarkId)
        });
    });

    // Sort categories by order
    const sortedCategories = Object.entries(categorized).sort((a, b) => {
        const orderA = benchmarksData.categories[a[0]]?.order || 999;
        const orderB = benchmarksData.categories[b[0]]?.order || 999;
        return orderA - orderB;
    });

    // Create optgroups
    sortedCategories.forEach(([categoryId, benchmarks]) => {
        const categoryMeta = benchmarksData.categories[categoryId];
        const optgroup = document.createElement('optgroup');
        optgroup.label = categoryMeta?.name || categoryId;

        // Sort benchmarks within category alphabetically
        benchmarks.sort((a, b) => a.meta.name.localeCompare(b.meta.name));

        benchmarks.forEach(benchmark => {
            const option = document.createElement('option');
            option.value = benchmark.id;
            option.textContent = `${benchmark.meta.name} (${benchmark.count} models)`;
            option.title = benchmark.meta.description; // Tooltip on hover
            optgroup.appendChild(option);
        });

        select.appendChild(optgroup);
    });

    // Set default benchmark (mmmlu)
    if (select.options.length > 0) {
        // Find and select the default benchmark
        for (let i = 0; i < select.options.length; i++) {
            if (select.options[i].value === currentBenchmark) {
                select.value = currentBenchmark;
                break;
            }
        }
        updateBenchmarkInfo(currentBenchmark);
    }
}

// Update benchmark info panel
function updateBenchmarkInfo(benchmarkId) {
    const meta = benchmarksData.benchmarks[benchmarkId];
    const infoPanel = document.getElementById('benchmark-info');

    if (!meta || !infoPanel) {
        if (infoPanel) infoPanel.style.display = 'none';
        return;
    }

    const nameEl = document.getElementById('benchmark-name');
    const descEl = document.getElementById('benchmark-description');
    const metaEl = document.getElementById('benchmark-meta');

    if (nameEl) nameEl.textContent = meta.full_name;
    if (descEl) descEl.textContent = meta.description;

    if (metaEl) {
        const count = countModelsForBenchmark(benchmarkId);
        metaEl.textContent = `Scale: ${meta.scale} • ${count} models with data`;
    }

    infoPanel.style.display = 'block';
}

// Get X value for a model based on current axis selection
function getXValue(model) {
    if (currentXAxis === 'active_parameters') {
        // For MoE models, use active parameters; dense models fall back to total
        if (model.active_parameters_billions || model.parameters_billions) {
            return model.active_parameters_billions || model.parameters_billions;
        }
        // Fall back to estimated parameters from pricing
        const estimated = estimateParameters(model);
        return estimated ? estimated.parameters_billions : null;
    } else if (currentXAxis === 'total_parameters') {
        // Use total parameters, or estimate from pricing
        if (model.parameters_billions) {
            return model.parameters_billions;
        }
        // Fall back to estimated parameters from pricing
        const estimated = estimateParameters(model);
        return estimated ? estimated.parameters_billions : null;
    } else if (currentXAxis === 'cost') {
        // For cost, use average of input and output costs
        if (model.pricing) {
            return (model.pricing.input_per_1m_tokens + model.pricing.output_per_1m_tokens) / 2;
        }
        // Fall back to estimated cost if no actual pricing
        const estimated = estimateCost(model);
        if (estimated) {
            return (estimated.input_per_1m_tokens + estimated.output_per_1m_tokens) / 2;
        }
        return null;
    }
    return null;
}

// Get Y value (benchmark score) for a model
function getYValue(model) {
    if (!model.benchmarks || !model.benchmarks[currentBenchmark]) {
        return null;
    }
    return model.benchmarks[currentBenchmark].score;
}

// Prepare data points for chart
function prepareDataPoints() {
    if (!modelsData || !modelsData.models) return [];

    return modelsData.models
        .filter(model => {
            // Filter by family
            if (currentFamily !== 'all' && model.family !== currentFamily) {
                return false;
            }

            // Ensure model has required data
            const x = getXValue(model);
            const y = getYValue(model);
            return x !== null && y !== null;
        })
        .map(model => ({
            x: getXValue(model),
            y: getYValue(model),
            model: model
        }));
}

// Calculate Pareto frontier
// For LLM metrics: maximize Y (benchmark score), minimize X (params/cost)
function calculateParetoFrontier(points) {
    if (points.length === 0) return [];

    // Sort by X ascending (lower is better)
    const sorted = [...points].sort((a, b) => a.x - b.x);

    const frontier = [];
    let maxY = -Infinity;

    for (const point of sorted) {
        // Point is on frontier if its Y is better than any previous point
        if (point.y > maxY) {
            frontier.push(point);
            maxY = point.y;
        }
    }

    return frontier;
}

// Render the chart
function renderChart() {
    const ctx = document.getElementById('pareto-chart').getContext('2d');

    // Prepare data points
    const dataPoints = prepareDataPoints();

    if (dataPoints.length === 0) {
        // No data to display
        if (chart) {
            chart.destroy();
        }
        ctx.font = '20px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('No data available for selected filters',
            ctx.canvas.width / 2, ctx.canvas.height / 2);
        return;
    }

    // Calculate Pareto frontier if enabled
    let frontierPoints = [];
    if (showPareto) {
        frontierPoints = calculateParetoFrontier(dataPoints);
    }

    // Group data points by provider for color coding
    const pointsByProvider = {};
    dataPoints.forEach(point => {
        const provider = point.model.provider;
        if (!pointsByProvider[provider]) {
            pointsByProvider[provider] = [];
        }
        pointsByProvider[provider].push(point);
    });

    // Create datasets - one per provider for color coding
    const datasets = Object.entries(pointsByProvider).map(([provider, points]) => {
        const color = getProviderColor(provider);
        return {
            label: provider,
            data: points,
            backgroundColor: color.bg,
            borderColor: color.border,
            borderWidth: 2,
            pointRadius: 6,
            pointHoverRadius: 8
        };
    });

    // Add Pareto frontier line with visible star markers
    if (showPareto && frontierPoints.length > 0) {
        datasets.push({
            label: 'Pareto Frontier',
            data: frontierPoints,
            backgroundColor: 'rgba(239, 68, 68, 0.8)',
            borderColor: 'rgba(239, 68, 68, 1)',
            borderWidth: 3,
            pointRadius: 10,  // Make points visible
            pointStyle: 'star',  // Use star shape for Pareto-optimal points
            pointHoverRadius: 12,
            showLine: true,
            fill: false,
            tension: 0,
            order: 0  // Draw Pareto points on top
        });
    }

    // Get axis labels
    const xLabels = {
        'active_parameters': 'Active Parameters (Billions)',
        'total_parameters': 'Total Parameters (Billions)',
        'cost': 'Average Cost per 1M Tokens ($)'
    };
    const xLabel = xLabels[currentXAxis] || 'X-Axis';
    const yLabel = getBenchmarkLabel(currentBenchmark);

    // Destroy existing chart
    if (chart) {
        chart.destroy();
    }

    // Create new chart
    chart = new Chart(ctx, {
        type: 'scatter',
        data: { datasets },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 2,
            plugins: {
                title: {
                    display: true,
                    text: `${yLabel} vs ${xLabel}`,
                    font: { size: 18 }
                },
                legend: {
                    display: false  // Hide legend - using data table instead
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const point = context.raw;
                            const model = point.model;
                            let label = `${model.name} (${model.provider})`;

                            // X-axis with descriptive label
                            let xLabel = '';
                            if (currentXAxis === 'cost') {
                                xLabel = `Cost: $${point.x.toFixed(2)} per 1M tokens`;
                                if (!model.pricing && estimateCost(model)) {
                                    xLabel += ' (estimated)';
                                }
                            } else if (currentXAxis === 'active_parameters') {
                                xLabel = `Active Parameters: ${point.x.toFixed(1)}B`;
                                if (!model.active_parameters_billions && !model.parameters_billions && estimateParameters(model)) {
                                    xLabel += ' (estimated)';
                                }
                            } else if (currentXAxis === 'total_parameters') {
                                xLabel = `Total Parameters: ${point.x.toFixed(1)}B`;
                                if (!model.parameters_billions && estimateParameters(model)) {
                                    xLabel += ' (estimated)';
                                }
                            }
                            label += `\n${xLabel}`;

                            // Y-axis with benchmark name
                            const benchName = benchmarksData.benchmarks[currentBenchmark]?.name || currentBenchmark.toUpperCase();
                            label += `\n${benchName}: ${point.y.toFixed(1)}`;

                            if (showCitations && model.benchmarks[currentBenchmark].source) {
                                const source = model.benchmarks[currentBenchmark].source;
                                label += `\nSource: ${source.type}`;
                                label += `\nCollected: ${source.collected}`;
                            }

                            return label.split('\n');
                        }
                    }
                }
            },
            scales: {
                x: {
                    type: 'logarithmic',
                    title: {
                        display: true,
                        text: xLabel
                    },
                    ticks: {
                        callback: function(value) {
                            const num = Number(value);
                            if (num >= 1000) {
                                return `${(num / 1000).toFixed(1)}k`;
                            }
                            if (num >= 1) {
                                return num.toFixed(1);
                            }
                            return num.toPrecision(2);
                        }
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: yLabel
                    }
                }
            },
            onClick: (event, elements) => {
                if (elements.length > 0) {
                    const element = elements[0];
                    const point = chart.data.datasets[element.datasetIndex].data[element.index];
                    showCitationPanel(point.model);
                }
            }
        }
    });
}

// Get human-readable benchmark label
function getBenchmarkLabel(benchmark) {
    const labels = {
        'mmlu': 'MMLU Score (%)',
        'mmmlu': 'MMMLU Score (%)',
        'humaneval': 'HumanEval Score (%)',
        'chatbot_arena_elo': 'Chatbot Arena ELO',
        'gsm8k': 'GSM8K Score (%)',
        'bbh': 'BBH Score (%)',
        'mbpp': 'MBPP Score (%)',
        'arenahard': 'ArenaHard Score (%)',
        'livebench': 'LiveBench Score (%)',
        'livecodebench': 'LiveCodeBench Score (%)',
        'swebench_verified': 'SWE-bench Verified (%)',
        'terminalbench': 'Terminal-bench (%)',
        'gpqa_diamond': 'GPQA Diamond (%)',
        'mmmu': 'MMMU Score (%)',
        'aime': 'AIME (%)',
        'aime2025': 'AIME 2025 (%)',
        'aime2025_no_tools': 'AIME 2025 No Tools (%)',
        'aime24': 'AIME\'24 Score (%)',
        'aime25': 'AIME\'25 Score (%)',
        'tau2bench_retail': 'τ2-bench Retail (%)',
        'tau2bench_airline': 'τ2-bench Airline (%)',
        'tau2bench_telecom': 'τ2-bench Telecom (%)',
        'osworld': 'OSWorld (%)',
        'finance_agent': 'Finance Agent (%)',
        'codeforces': 'CodeForces ELO',
        'aider': 'Aider Score (%)',
        'gpqa': 'GPQA Score (%)',
        'bfcl': 'BFCL Score (%)',
        'multiif': 'MultiIF Score (%)'
    };
    return labels[benchmark] || benchmark;
}

// Show citation panel for a model
function showCitationPanel(model) {
    const panel = document.getElementById('citation-panel');
    const content = document.getElementById('citation-content');

    let html = `<h4>${model.name} (${model.provider})</h4>`;

    // Benchmark citation
    if (model.benchmarks[currentBenchmark]) {
        const bench = model.benchmarks[currentBenchmark];
        html += `<p><strong>${getBenchmarkLabel(currentBenchmark)}:</strong> ${bench.score}</p>`;
        if (bench.source) {
            html += `<p><strong>Source:</strong> <a href="${bench.source.url}" target="_blank">${bench.source.url}</a></p>`;
            html += `<p><strong>Type:</strong> ${bench.source.type}</p>`;
            html += `<p><strong>Collected:</strong> ${bench.source.collected}</p>`;
            if (bench.source.notes) {
                html += `<p><strong>Notes:</strong> ${bench.source.notes}</p>`;
            }
        }
    }

    // Parameters citation
    if (model.parameters_billions && model.parameters_source) {
        html += `<p><strong>Parameters:</strong> ${model.parameters_billions}B</p>`;
        html += `<p><strong>Source:</strong> <a href="${model.parameters_source.url}" target="_blank">${model.parameters_source.url}</a></p>`;
        html += `<p><strong>Collected:</strong> ${model.parameters_source.collected}</p>`;
        if (model.parameters_source.notes) {
            html += `<p><strong>Notes:</strong> ${model.parameters_source.notes}</p>`;
        }
    }

    // Pricing citation
    if (model.pricing && model.pricing.source) {
        html += `<p><strong>Pricing:</strong> $${model.pricing.input_per_1m_tokens.toFixed(2)} / $${model.pricing.output_per_1m_tokens.toFixed(2)} per 1M tokens</p>`;
        html += `<p><strong>Source:</strong> <a href="${model.pricing.source.url}" target="_blank">${model.pricing.source.url}</a></p>`;
        html += `<p><strong>Collected:</strong> ${model.pricing.source.collected}</p>`;
    }

    content.innerHTML = html;
    panel.style.display = 'block';
}

// Render data table/cards showing all models
function renderDataTable() {
    const container = document.getElementById('models-table');
    if (!container) return;

    // Get filtered models (same as chart)
    const dataPoints = prepareDataPoints();

    if (dataPoints.length === 0) {
        container.innerHTML = '<p class="no-data">No models match the current filters.</p>';
        return;
    }

    // Calculate Pareto frontier to mark optimal models
    const frontierPoints = calculateParetoFrontier(dataPoints);
    const frontierIds = new Set(frontierPoints.map(p => p.model.id));

    // Sort by current benchmark score (descending)
    const sortedPoints = [...dataPoints].sort((a, b) => b.y - a.y);

    // Generate cards HTML
    let html = '<div class="model-cards-grid">';

    sortedPoints.forEach(point => {
        const model = point.model;
        const color = getProviderColor(model.provider);
        const benchScore = model.benchmarks[currentBenchmark]?.score;
        const isParetoOptimal = frontierIds.has(model.id);

        html += `
            <div class="model-card" data-model-id="${model.id}" style="border-left: 4px solid ${color.border}">
                <div class="model-card-header">
                    <h3 class="model-name">
                        ${model.name}
                        ${isParetoOptimal ? '<span class="pareto-badge" title="Pareto-optimal: Best tradeoff between performance and cost/size">⭐</span>' : ''}
                    </h3>
                    <span class="model-provider" style="background-color: ${color.bg}; border-color: ${color.border}">
                        ${model.provider}
                    </span>
                </div>

                <div class="model-card-stats">
                    <div class="stat">
                        <span class="stat-label">Parameters</span>
                        ${model.parameters_source ? `
                            <a href="${model.parameters_source.url}" target="_blank"
                               class="stat-value stat-link ${model.parameters_source.type === 'estimated' ? 'estimated' : ''}"
                               title="Source: ${model.parameters_source.type}${model.parameters_source.notes ? ' - ' + model.parameters_source.notes : ''} (${model.parameters_source.collected})">
                                ${model.parameters_source.type === 'estimated' ? '≈ ' : ''}${
                                model.active_parameters_billions
                                    ? `${model.active_parameters_billions}B / ${model.parameters_billions}B`
                                    : `${model.parameters_billions}B`
                                } ↗
                            </a>
                        ` : model.parameters_billions ? `
                            <span class="stat-value">
                                ${model.parameters_billions}B
                            </span>
                        ` : estimateParameters(model) ? `
                            <span class="stat-value estimated" title="Estimated from pricing">
                                ~${estimateParameters(model).parameters_billions.toFixed(0)}B
                            </span>
                        ` : `
                            <span class="stat-value">?</span>
                        `}
                    </div>
                    <div class="stat">
                        <span class="stat-label">${getBenchmarkLabel(currentBenchmark)}</span>
                        ${model.benchmarks[currentBenchmark]?.source ? `
                            <a href="${model.benchmarks[currentBenchmark].source.url}" target="_blank"
                               class="stat-value stat-link"
                               title="Source: ${model.benchmarks[currentBenchmark].source.type}${model.benchmarks[currentBenchmark].source.notes ? ' - ' + model.benchmarks[currentBenchmark].source.notes : ''} (${model.benchmarks[currentBenchmark].source.collected})">
                                ${benchScore.toFixed(1)} ↗
                            </a>
                        ` : `
                            <span class="stat-value">${benchScore ? benchScore.toFixed(1) : 'N/A'}</span>
                        `}
                    </div>
                    <div class="stat">
                        <span class="stat-label">Input/1M</span>
                        ${model.pricing?.source ? `
                            <a href="${model.pricing.source.url}" target="_blank"
                               class="stat-value stat-link"
                               title="Source: ${model.pricing.source.type}${model.pricing.source.notes ? ' - ' + model.pricing.source.notes : ''} (${model.pricing.source.collected})">
                                $${model.pricing.input_per_1m_tokens.toFixed(2)} ↗
                            </a>
                        ` : `
                            <span class="stat-value" ${estimateCost(model) ? 'title="Estimated from parameter count"' : ''}>
                                ${model.pricing ? '$' + model.pricing.input_per_1m_tokens.toFixed(2) :
                                  estimateCost(model) ? '~$' + estimateCost(model).input_per_1m_tokens.toFixed(2) : 'N/A'}
                            </span>
                        `}
                    </div>
                    <div class="stat">
                        <span class="stat-label">Output/1M</span>
                        ${model.pricing?.source ? `
                            <a href="${model.pricing.source.url}" target="_blank"
                               class="stat-value stat-link"
                               title="Source: ${model.pricing.source.type}${model.pricing.source.notes ? ' - ' + model.pricing.source.notes : ''} (${model.pricing.source.collected})">
                                $${model.pricing.output_per_1m_tokens.toFixed(2)} ↗
                            </a>
                        ` : `
                            <span class="stat-value" ${estimateCost(model) ? 'title="Estimated from parameter count"' : ''}>
                                ${model.pricing ? '$' + model.pricing.output_per_1m_tokens.toFixed(2) :
                                  estimateCost(model) ? '~$' + estimateCost(model).output_per_1m_tokens.toFixed(2) : 'N/A'}
                            </span>
                        `}
                    </div>
                </div>

                <div class="model-card-benchmarks">
                    ${Object.entries(model.benchmarks || {})
                        .map(([bench, data]) => {
                            if (data.source) {
                                return `
                                    <a href="${data.source.url}" target="_blank"
                                       class="benchmark-chip benchmark-chip-link"
                                       title="Source: ${data.source.type}${data.source.notes ? ' - ' + data.source.notes : ''} (${data.source.collected})">
                                        <span class="bench-name">${bench.toUpperCase()}</span>
                                        <span class="bench-score">${data.score.toFixed(1)} ↗</span>
                                    </a>
                                `;
                            } else {
                                return `
                                    <div class="benchmark-chip">
                                        <span class="bench-name">${bench.toUpperCase()}</span>
                                        <span class="bench-score">${data.score.toFixed(1)}</span>
                                    </div>
                                `;
                            }
                        })
                        .join('')}
                </div>
            </div>
        `;
    });

    html += '</div>';
    container.innerHTML = html;

    // Add hover event listeners to highlight chart points
    const cards = container.querySelectorAll('.model-card');
    cards.forEach((card, cardIndex) => {
        const modelId = card.dataset.modelId;

        card.addEventListener('mouseenter', () => {
            highlightChartPoint(modelId);
        });

        card.addEventListener('mouseleave', () => {
            clearChartHighlight();
        });
    });
}

// Highlight a chart point by model ID
function highlightChartPoint(modelId) {
    if (!chart) return;

    // Find the dataset and point index for this model
    let foundDatasetIndex = -1;
    let foundPointIndex = -1;

    chart.data.datasets.forEach((dataset, datasetIndex) => {
        if (dataset.label === 'Pareto Frontier') return; // Skip Pareto line

        dataset.data.forEach((point, pointIndex) => {
            if (point.model && point.model.id === modelId) {
                foundDatasetIndex = datasetIndex;
                foundPointIndex = pointIndex;
            }
        });
    });

    if (foundDatasetIndex !== -1 && foundPointIndex !== -1) {
        // Highlight the point using Chart.js API
        chart.setActiveElements([{
            datasetIndex: foundDatasetIndex,
            index: foundPointIndex
        }]);
        chart.tooltip.setActiveElements([{
            datasetIndex: foundDatasetIndex,
            index: foundPointIndex
        }]);
        chart.update('none'); // Update without animation
    }
}

// Clear chart point highlighting
function clearChartHighlight() {
    if (!chart) return;

    chart.setActiveElements([]);
    chart.tooltip.setActiveElements([]);
    chart.update('none');
}
