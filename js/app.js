// Global state
let modelsData = null;
let chart = null;
let currentBenchmark = 'mmlu';
let currentXAxis = 'parameters';
let currentFamily = 'all';
let showPareto = true;
let showCitations = false;

// Brand colors for providers
const PROVIDER_COLORS = {
    'OpenAI': { bg: 'rgba(16, 163, 127, 0.7)', border: 'rgba(16, 163, 127, 1)' },      // OpenAI green
    'Anthropic': { bg: 'rgba(204, 85, 51, 0.7)', border: 'rgba(204, 85, 51, 1)' },     // Anthropic orange
    'Google': { bg: 'rgba(66, 133, 244, 0.7)', border: 'rgba(66, 133, 244, 1)' },      // Google blue
    'Meta': { bg: 'rgba(0, 102, 255, 0.7)', border: 'rgba(0, 102, 255, 1)' },          // Meta blue
    'xAI': { bg: 'rgba(0, 0, 0, 0.7)', border: 'rgba(0, 0, 0, 1)' },                   // xAI black
    'Mistral': { bg: 'rgba(255, 122, 0, 0.7)', border: 'rgba(255, 122, 0, 1)' },       // Mistral orange
    'default': { bg: 'rgba(107, 114, 128, 0.7)', border: 'rgba(107, 114, 128, 1)' }    // Gray fallback
};

// Get color for a provider
function getProviderColor(provider) {
    return PROVIDER_COLORS[provider] || PROVIDER_COLORS['default'];
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', async () => {
    await loadData();
    initControls();
    renderChart();
    renderDataTable();
});

// Load data from JSON file
async function loadData() {
    try {
        const response = await fetch('data/models.json');
        modelsData = await response.json();

        // Update last updated timestamp
        if (modelsData.last_updated) {
            const date = new Date(modelsData.last_updated);
            document.getElementById('last-updated').textContent =
                `Last Updated: ${date.toLocaleDateString()}`;
        }
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

    document.getElementById('show-pareto').addEventListener('change', (e) => {
        showPareto = e.target.checked;
        renderChart();
    });

    document.getElementById('show-citations').addEventListener('change', (e) => {
        showCitations = e.target.checked;
    });
}

// Get X value for a model based on current axis selection
function getXValue(model) {
    if (currentXAxis === 'parameters') {
        return model.parameters_billions || null;
    } else {
        // For cost, use average of input and output costs
        if (model.pricing) {
            return (model.pricing.input_per_1m_tokens + model.pricing.output_per_1m_tokens) / 2;
        }
        return null;
    }
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

    // Add Pareto frontier line
    if (showPareto && frontierPoints.length > 0) {
        datasets.push({
            label: 'Pareto Frontier',
            data: frontierPoints,
            backgroundColor: 'rgba(239, 68, 68, 0)',
            borderColor: 'rgba(239, 68, 68, 1)',
            borderWidth: 3,
            pointRadius: 0,
            showLine: true,
            fill: false,
            tension: 0
        });
    }

    // Get axis labels
    const xLabel = currentXAxis === 'parameters'
        ? 'Parameters (Billions)'
        : 'Average Cost per 1M Tokens ($)';
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
                            label += `\nX: ${point.x.toFixed(2)}`;
                            label += `\nY: ${point.y.toFixed(2)}`;

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
                    title: {
                        display: true,
                        text: xLabel
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
        'humaneval': 'HumanEval Score (%)',
        'chatbot_arena_elo': 'Chatbot Arena ELO',
        'gsm8k': 'GSM8K Score (%)',
        'bbh': 'BBH Score (%)',
        'mbpp': 'MBPP Score (%)'
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

    // Sort by current benchmark score (descending)
    const sortedPoints = [...dataPoints].sort((a, b) => b.y - a.y);

    // Generate cards HTML
    let html = '<div class="model-cards-grid">';

    sortedPoints.forEach(point => {
        const model = point.model;
        const color = getProviderColor(model.provider);
        const benchScore = model.benchmarks[currentBenchmark]?.score;

        html += `
            <div class="model-card" style="border-left: 4px solid ${color.border}">
                <div class="model-card-header">
                    <h3 class="model-name">${model.name}</h3>
                    <span class="model-provider" style="background-color: ${color.bg}; border-color: ${color.border}">
                        ${model.provider}
                    </span>
                </div>

                <div class="model-card-stats">
                    <div class="stat">
                        <span class="stat-label">Parameters</span>
                        <span class="stat-value">${model.parameters_billions || '?'}B</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">${getBenchmarkLabel(currentBenchmark)}</span>
                        <span class="stat-value">${benchScore ? benchScore.toFixed(1) : 'N/A'}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Input/1M</span>
                        <span class="stat-value">
                            ${model.pricing ? '$' + model.pricing.input_per_1m_tokens.toFixed(2) : 'N/A'}
                        </span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Output/1M</span>
                        <span class="stat-value">
                            ${model.pricing ? '$' + model.pricing.output_per_1m_tokens.toFixed(2) : 'N/A'}
                        </span>
                    </div>
                </div>

                <div class="model-card-benchmarks">
                    ${Object.entries(model.benchmarks || {})
                        .map(([bench, data]) => `
                            <div class="benchmark-chip">
                                <span class="bench-name">${bench.toUpperCase()}</span>
                                <span class="bench-score">${data.score.toFixed(1)}</span>
                            </div>
                        `)
                        .join('')}
                </div>

                ${showCitations ? `
                    <div class="model-card-citations">
                        ${model.benchmarks[currentBenchmark]?.source
                            ? `<a href="${model.benchmarks[currentBenchmark].source.url}" target="_blank" class="citation-link">
                                📄 ${model.benchmarks[currentBenchmark].source.type} source
                               </a>`
                            : ''}
                    </div>
                ` : ''}
            </div>
        `;
    });

    html += '</div>';
    container.innerHTML = html;
}
