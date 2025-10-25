// Global variables
let currentRange = 'all';
let charts = {};
let statsData = null;

// Initialize charts
function initCharts() {
    // Accuracy Breakdown Chart
    const accuracyCtx = document.getElementById('accuracyChart').getContext('2d');
    charts.accuracy = new Chart(accuracyCtx, {
        type: 'bar',
        data: {
            labels: ['Overall', 'Rain Predictions', 'No Rain Predictions'],
            datasets: [{
                label: 'Accuracy (%)',
                data: [0, 0, 0],
                backgroundColor: [
                    'rgba(52, 152, 219, 0.8)',
                    'rgba(46, 204, 113, 0.8)',
                    'rgba(241, 196, 15, 0.8)'
                ],
                borderColor: [
                    'rgba(52, 152, 219, 1)',
                    'rgba(46, 204, 113, 1)',
                    'rgba(241, 196, 15, 1)'
                ],
                borderWidth: 2,
                borderRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.parsed.x.toFixed(2) + '%';
                        }
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                }
            }
        }
    });

    // Rainfall Comparison Chart
    const rainfallCtx = document.getElementById('rainfallChart').getContext('2d');
    charts.rainfall = new Chart(rainfallCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Actual Rainfall',
                    data: [],
                    borderColor: 'rgba(52, 152, 219, 1)',
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true
                },
                {
                    label: 'Predicted Rainfall',
                    data: [],
                    borderColor: 'rgba(231, 76, 60, 1)',
                    backgroundColor: 'rgba(231, 76, 60, 0.1)',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    tension: 0.4,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' + context.parsed.y.toFixed(2) + ' mm';
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return value + ' mm';
                        }
                    }
                }
            }
        }
    });

    // Confusion Matrix Chart (Grouped Bar)
    const distributionCtx = document.getElementById('distributionChart').getContext('2d');
    charts.distribution = new Chart(distributionCtx, {
        type: 'bar',
        data: {
            labels: ['Rain', 'No Rain'],
            datasets: [
                {
                    label: 'True Positive / True Negative',
                    data: [0, 0],
                    backgroundColor: 'rgba(46, 204, 113, 0.8)',
                    borderColor: 'rgba(46, 204, 113, 1)',
                    borderWidth: 2,
                    borderRadius: 8
                },
                {
                    label: 'False Positive / False Negative',
                    data: [0, 0],
                    backgroundColor: 'rgba(231, 76, 60, 0.8)',
                    borderColor: 'rgba(231, 76, 60, 1)',
                    borderWidth: 2,
                    borderRadius: 8
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const datasetLabel = context.dataset.label;
                            const categoryLabel = context.label;
                            let fullLabel = '';
                            
                            if (categoryLabel === 'Rain') {
                                fullLabel = datasetLabel.includes('True') ? 'True Positive' : 'False Positive';
                            } else {
                                fullLabel = datasetLabel.includes('True') ? 'True Negative' : 'False Negative';
                            }
                            
                            return fullLabel + ': ' + context.parsed.y.toLocaleString();
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });

    // Feature Impact Chart
    const featureCtx = document.getElementById('featureChart').getContext('2d');
    charts.feature = new Chart(featureCtx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Accuracy (%)',
                data: [],
                backgroundColor: 'rgba(155, 89, 182, 0.8)',
                borderColor: 'rgba(155, 89, 182, 1)',
                borderWidth: 2,
                borderRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return 'Accuracy: ' + context.parsed.y.toFixed(2) + '%';
                        },
                        afterLabel: function(context) {
                            const index = context.dataIndex;
                            const counts = charts.feature.data.counts || [];
                            if (counts[index]) {
                                return 'Count: ' + counts[index].toLocaleString();
                            }
                            return '';
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                }
            }
        }
    });
}

// Fetch statistics data
function fetchStatistics(range) {
    $('.loading-indicator').show();
    
    $.ajax({
        url: '/api/statistics?range=' + range,
        type: 'GET',
        success: function(data) {
            statsData = data;
            updateMetrics(data);
            updateCharts(data);
            $('.loading-indicator').hide();
        },
        error: function() {
            $('.loading-indicator').hide();
            alert('Error loading statistics data');
        }
    });
}

// Update metric cards
function updateMetrics(data) {
    $('#metric-total').text(data.total_predictions.toLocaleString());
    $('#metric-rain').text(data.rain_count.toLocaleString());
    $('#metric-no-rain').text(data.no_rain_count.toLocaleString());
    $('#metric-accuracy').text(data.overall_accuracy.toFixed(2) + '%');
}

// Update all charts
function updateCharts(data) {
    // Update Accuracy Chart
    charts.accuracy.data.datasets[0].data = [
        data.overall_accuracy,
        data.rain_accuracy,
        data.no_rain_accuracy
    ];
    charts.accuracy.update();

    // Update Rainfall Chart
    const rainfallData = data.rainfall_comparison || [];
    charts.rainfall.data.labels = rainfallData.map(d => d.date);
    charts.rainfall.data.datasets[0].data = rainfallData.map(d => d.actual);
    charts.rainfall.data.datasets[1].data = rainfallData.map(d => d.predicted);
    charts.rainfall.update();

    // Update Confusion Matrix Chart
    const cm = data.confusion_matrix || {};
    charts.distribution.data.datasets[0].data = [
        cm.true_positive || 0,  // Predicted Rain = Actual Rain (green)
        cm.true_negative || 0   // Predicted No Rain = Actual No Rain (green)
    ];
    charts.distribution.data.datasets[1].data = [
        cm.false_positive || 0, // Predicted Rain, Actual No Rain (red)
        cm.false_negative || 0  // Predicted No Rain, Actual Rain (red - DANGEROUS!)
    ];
    charts.distribution.update();

    // Update Feature Chart (default: temperature)
    updateFeatureChart('temperature');
    
    // Load Error Clusters
    loadErrorClusters(currentRange);
}

// Update feature impact chart
function updateFeatureChart(feature) {
    if (!statsData || !statsData.feature_impact || !statsData.feature_impact[feature]) {
        return;
    }

    const featureData = statsData.feature_impact[feature];
    const labels = Object.keys(featureData);
    const accuracies = labels.map(key => featureData[key].accuracy);
    const counts = labels.map(key => featureData[key].count);

    charts.feature.data.labels = labels;
    charts.feature.data.datasets[0].data = accuracies;
    charts.feature.data.counts = counts; // Store for tooltip
    charts.feature.update();
}

// Load error clusters analysis
function loadErrorClusters(range = 'all') {
    const container = $('#error-clusters-content');
    container.html('<div class="loading-state"><i class="fas fa-spinner fa-spin"></i> Running K-Means clustering analysis...</div>');
    
    $.ajax({
        url: `/api/error-clusters?range=${range}`,
        method: 'GET',
        success: function(data) {
            if (data.error) {
                container.html(`
                    <div class="error-state">
                        <i class="fas fa-exclamation-circle"></i>
                        <p>${data.message || data.error}</p>
                        <small>Total incorrect predictions: ${data.count || 0}</small>
                    </div>
                `);
                return;
            }
            
            // Render cluster summary
            let html = `
                <div class="cluster-summary">
                    <h4><i class="fas fa-chart-pie"></i> Clustering Summary</h4>
                    <p>${data.summary}</p>
                </div>
                <div class="cluster-grid">
            `;
            
            // Render each cluster
            data.clusters.forEach((cluster, index) => {
                const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];
                const color = colors[index % colors.length];
                
                html += `
                    <div class="cluster-card" style="border-left: 4px solid ${color}">
                        <div class="cluster-header">
                            <span class="cluster-title">
                                <i class="fas fa-layer-group"></i> Cluster ${cluster.cluster_id}
                            </span>
                            <span class="cluster-size">${cluster.size} errors (${cluster.percentage}%)</span>
                        </div>
                        
                        <div class="cluster-stats">
                            <div class="stat-row">
                                <span class="stat-label"><i class="fas fa-temperature-high"></i> Avg Temperature</span>
                                <span class="stat-value">${cluster.characteristics.tempC.mean}°C</span>
                            </div>
                            <div class="stat-row">
                                <span class="stat-label"><i class="fas fa-tint"></i> Avg Humidity</span>
                                <span class="stat-value">${cluster.characteristics.humidity.mean}%</span>
                            </div>
                            <div class="stat-row">
                                <span class="stat-label"><i class="fas fa-compress-arrows-alt"></i> Avg Pressure</span>
                                <span class="stat-value">${cluster.characteristics.pressure.mean} mb</span>
                            </div>
                            <div class="stat-row">
                                <span class="stat-label"><i class="fas fa-wind"></i> Avg Wind Speed</span>
                                <span class="stat-value">${cluster.characteristics.windspeedKmph.mean} km/h</span>
                            </div>
                        </div>
                        
                        <div class="error-types">
                            <div class="error-type-badge false-positive">
                                <i class="fas fa-times-circle"></i> Failed alarms: ${cluster.error_types.over_predicted}
                            </div>
                            <div class="error-type-badge false-negative">
                                <i class="fas fa-exclamation-triangle"></i> Missed rain: ${cluster.error_types.under_predicted}
                            </div>
                        </div>
                        
                        <div class="cluster-insight">
                            <i class="fas fa-lightbulb"></i> ${cluster.insight}
                        </div>
                    </div>
                `;
            });
            
            html += '</div>';
            container.html(html);
        },
        error: function(xhr, status, error) {
            container.html(`
                <div class="error-state">
                    <i class="fas fa-exclamation-circle"></i>
                    <p>Failed to load error clustering analysis</p>
                    <small>${error}</small>
                </div>
            `);
        }
    });
}

// Event handlers
$(document).ready(function() {
    // Initialize charts
    initCharts();

    // Load initial data
    fetchStatistics('all');

    // Filter buttons
    $('.filter-btn').on('click', function() {
        $('.filter-btn').removeClass('active');
        $(this).addClass('active');
        
        const range = $(this).data('range');
        currentRange = range;
        fetchStatistics(range);
    });

    // Feature tabs
    $('.tab-btn').on('click', function() {
        $('.tab-btn').removeClass('active');
        $(this).addClass('active');
        
        const feature = $(this).data('feature');
        updateFeatureChart(feature);
    });
});
