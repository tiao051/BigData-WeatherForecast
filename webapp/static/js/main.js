// Global variables
let totalRainCount = 0;
let totalRealtimeCount = 0; // Total count of all realtime predictions since page load (unlimited)
let socket;
let currentPage = 1; // Always start at page 1 on page load (newest data first)
const PAGE_SIZE = 50;

// Update statistics display
function updateStats(totalCount, rainCount) {
    $('#total-predictions').text(totalCount);
    $('#rain-count').text(rainCount);
}

// Get status badge HTML
function getStatusBadge(actual, predicted) {
    if (actual === predicted) {
        return '<span class="status-badge correct"><i class="fas fa-check"></i> Correct</span>';
    } else {
        return '<span class="status-badge incorrect"><i class="fas fa-times"></i> Incorrect</span>';
    }
}

// Get weather badge HTML
function getWeatherBadge(weather) {
    if (weather === 'rain') {
        return '<span class="weather-badge rain-badge"><i class="fas fa-cloud-rain"></i> Rain</span>';
    } else {
        return '<span class="weather-badge clear-badge"><i class="fas fa-sun"></i> No Rain</span>';
    }
}

// Render table data
function renderTableData(data) {
    // Remove empty state if exists
    $('.empty-state').remove();
    
    var tableContent = '';
    data.forEach(function(predict, index) {
        const actualRainfall = parseFloat(predict.precip_mm_origin || predict.precipMM_origin || 0).toFixed(2);
        const predictedRainfall = parseFloat(predict.rain_prediction || 0).toFixed(2);
        tableContent += '<tr>' +
            '<td><span class="row-number">' + (((currentPage - 1) * PAGE_SIZE) + index + 1) + '</span></td>' +
            '<td>' + getWeatherBadge(predict.predict_origin) + '</td>' +
            '<td>' + getWeatherBadge(predict.predict) + '</td>' +
            '<td><span class="rainfall-value">' + actualRainfall + '</span></td>' +
            '<td><span class="rainfall-value predicted">' + predictedRainfall + '</span></td>' +
            '<td><span class="date-text">' + predict.date + '</span></td>' +
            '<td><span class="time-text">' + predict.time + '</span></td>' +
            '<td>' + getStatusBadge(predict.predict_origin, predict.predict) + '</td>' +
        '</tr>';
    });
    $('#predict-table-body').html(tableContent);
}

// Handle new prediction from WebSocket (single record)
function handleNewPrediction(data) {
    const prediction = data.prediction;
    
    // Increment total realtime count (unlimited - tracks all predictions since page load)
    totalRealtimeCount++;
    
    // Update rain count
    if (prediction.predict === 'rain') {
        totalRainCount++;
    }

    // Update stats with total realtime count (not limited)
    updateStats(totalRealtimeCount, totalRainCount);

    // If user is on first page, prepend to table with 50-record limit enforcement
    if (currentPage === 1) {
        prependNewRow(prediction);  // This function enforces PAGE_SIZE limit
    }
    // If user is on other pages, just update counters (no notification)
}

// Prepend single new row with animation (used for real-time updates on page 1)
function prependNewRow(predict) {
    // Remove empty state if exists
    $('.empty-state').remove();
    
    const actualRainfall = parseFloat(predict.precip_mm_origin || predict.precipMM_origin || 0).toFixed(2);
    const predictedRainfall = parseFloat(predict.rain_prediction || 0).toFixed(2);
    
    const rowHtml = '<tr>' +
        '<td><span class="row-number">1</span></td>' +
        '<td>' + getWeatherBadge(predict.predict_origin) + '</td>' +
        '<td>' + getWeatherBadge(predict.predict) + '</td>' +
        '<td><span class="rainfall-value">' + actualRainfall + '</span></td>' +
        '<td><span class="rainfall-value predicted">' + predictedRainfall + '</span></td>' +
        '<td><span class="date-text">' + predict.date + '</span></td>' +
        '<td><span class="time-text">' + predict.time + '</span></td>' +
        '<td>' + getStatusBadge(predict.predict_origin, predict.predict) + '</td>' +
    '</tr>';
    
    $('#predict-table-body').prepend(rowHtml);
    
    // IMMEDIATELY enforce PAGE_SIZE limit - remove excess rows synchronously
    const totalRows = $('#predict-table-body tr').length;
    if (totalRows > PAGE_SIZE) {
        // Remove all excess rows beyond PAGE_SIZE
        $('#predict-table-body tr').slice(PAGE_SIZE).remove();
    }
    
    // Update all row numbers
    updateAllRowNumbers();
}

// Update all row numbers
function updateAllRowNumbers() {
    $('#predict-table-body tr').each(function(index) {
        $(this).find('.row-number').text(((currentPage - 1) * PAGE_SIZE) + index + 1);
    });
}

// Initialize WebSocket (Socket.IO) connection
function initWebSocket() {
    try {
        socket = io();

        socket.on('connect', function() {
            console.log('Socket connected:', socket.id);
        });

        socket.on('disconnect', function(reason) {
            console.warn('Socket disconnected:', reason);
        });

        // Listen for new_prediction events from server
        socket.on('new_prediction', function(msg) {
            try {
                // server emits { 'prediction': { ... } }
                handleNewPrediction(msg);
            } catch (e) {
                console.error('Error handling new_prediction:', e);
            }
        });

    } catch (e) {
        console.error('WebSocket init error:', e);
    }
}

// Render page buttons
function renderPageButtons(totalPages, currentPage) {
    const pageButtonsContainer = $('#page-buttons');
    pageButtonsContainer.empty();
    
    const maxVisiblePages = 5; // Show max 5 page buttons
    let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
    let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);
    
    if (endPage - startPage + 1 < maxVisiblePages) {
        startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }
    
    for (let i = startPage; i <= endPage; i++) {
        const button = $('<button class="btn btn-outline-primary page-btn"></button>')
            .text(i)
            .data('page', i);
        
        if (i === currentPage) {
            button.addClass('active').removeClass('btn-outline-primary').addClass('btn-primary');
        }
        
        button.on('click', function() {
            const page = $(this).data('page');
            console.log('Page button clicked:', page);
            currentPage = page;
            loadPage(currentPage);
        });
        
        pageButtonsContainer.append(button);
    }
}

// Load paginated data from backend (GLOBAL function - can be called from anywhere)
function loadPage(page) {
    $.get('/get-data', { page: page, per_page: PAGE_SIZE }, function(res) {
        // update current page based on server response
        currentPage = res.pagination.page;
        renderTableData(res.data);
        updateStats(res.pagination.total_count, res.pagination.rain_count);
        $('#pagination-info').text('Page ' + res.pagination.page + ' of ' + res.pagination.total_pages);
        $('#prev-page-btn').prop('disabled', !res.pagination.has_prev);
        $('#next-page-btn').prop('disabled', !res.pagination.has_next);
        renderPageButtons(res.pagination.total_pages, res.pagination.page);
    });
}

// Initialize on document ready
$(document).ready(function() {
    // Reset counters on page refresh
    totalRainCount = 0;
    totalRealtimeCount = 0; // Reset total realtime count on refresh
    
    // Set initial stats to 0 (will increment as realtime predictions arrive)
    updateStats(0, 0);

    // Initial load
    loadPage(currentPage);

    // Pagination button events
    $('#prev-page-btn').on('click', function() {
        if (currentPage > 1) {
            currentPage--;
            loadPage(currentPage);
        }
    });
    $('#next-page-btn').on('click', function() {
        currentPage++;
        loadPage(currentPage);
    });

    // Initialize WebSocket for real-time updates
    initWebSocket();

});
