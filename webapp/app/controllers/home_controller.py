from flask import render_template, jsonify, request
from bson import ObjectId
import datetime
import pytz
import json
from pymongo import DESCENDING
from database.mongodb import db

# Vietnam timezone
VN_TZ = pytz.timezone('Asia/Ho_Chi_Minh')

# Cache for total count to avoid expensive count queries
_cached_count = {'value': 0, 'last_update': None}
_cached_rain_count = {'value': 0, 'last_update': None}

def get_cached_count():
    """Get cached total count, refresh every 10 seconds"""
    now = datetime.datetime.now()
    if (_cached_count['last_update'] is None or 
        (now - _cached_count['last_update']).seconds > 10):
        # Use estimated count for speed (acceptable for large datasets)
        _cached_count['value'] = db.predict.estimated_document_count()
        _cached_count['last_update'] = now
    return _cached_count['value']

def get_cached_rain_count():
    """Get cached rain prediction count, refresh every 10 seconds"""
    now = datetime.datetime.now()
    if (_cached_rain_count['last_update'] is None or 
        (now - _cached_rain_count['last_update']).seconds > 10):
        # Count predictions where predict='rain'
        _cached_rain_count['value'] = db.predict.count_documents({'predict': 'rain'})
        _cached_rain_count['last_update'] = now
    return _cached_rain_count['value']

def invalidate_count_cache():
    """Invalidate the cached count - call this when new data is inserted"""
    global _cached_count, _cached_rain_count
    _cached_count['last_update'] = None
    _cached_rain_count['last_update'] = None

def home():
    # Real-time monitoring page (no initial data - loads from MongoDB via /get-data endpoint)
    return render_template('home.html')

def statistics():
    # Statistics dashboard page
    return render_template('statistics.html')

def get_statistics():
    """Get comprehensive statistics for dashboard"""
    # Get time range filter (default: all time)
    time_range = request.args.get('range', 'all')
    
    # Calculate date filter
    query_filter = {}
    if time_range != 'all':
        from datetime import timedelta
        now = datetime.datetime.now(VN_TZ)
        
        range_map = {
            '7d': 7,
            '30d': 30,
            '90d': 90,
        }
        
        if time_range in range_map:
            days = range_map[time_range]
            start_date = now - timedelta(days=days)
            query_filter['predicted_at'] = {'$gte': start_date}
    
    # Get all predictions with filter
    predictions = list(db.predict.find(query_filter))
    
    if not predictions:
        return jsonify({
            'total_predictions': 0,
            'rain_count': 0,
            'no_rain_count': 0,
            'overall_accuracy': 0,
            'rain_accuracy': 0,
            'no_rain_accuracy': 0,
            'correct_predictions': 0,
            'incorrect_predictions': 0,
            'rainfall_comparison': [],
            'feature_impact': {}
        })
    
    total = len(predictions)
    correct = sum(1 for p in predictions if p.get('predict') == p.get('predict_origin'))
    incorrect = total - correct
    
    # Calculate Confusion Matrix
    true_positive = sum(1 for p in predictions if p.get('predict') == 'rain' and p.get('predict_origin') == 'rain')
    false_positive = sum(1 for p in predictions if p.get('predict') == 'rain' and p.get('predict_origin') != 'rain')
    true_negative = sum(1 for p in predictions if p.get('predict') != 'rain' and p.get('predict_origin') != 'rain')
    false_negative = sum(1 for p in predictions if p.get('predict') != 'rain' and p.get('predict_origin') == 'rain')
    
    # Count rain/no-rain predictions
    rain_predictions = [p for p in predictions if p.get('predict') == 'rain']
    no_rain_predictions = [p for p in predictions if p.get('predict') != 'rain']
    
    rain_count = len(rain_predictions)
    no_rain_count = len(no_rain_predictions)
    
    # Calculate accuracies
    overall_accuracy = (correct / total * 100) if total > 0 else 0
    
    rain_correct = sum(1 for p in rain_predictions if p.get('predict') == p.get('predict_origin'))
    rain_accuracy = (rain_correct / rain_count * 100) if rain_count > 0 else 0
    
    no_rain_correct = sum(1 for p in no_rain_predictions if p.get('predict') == p.get('predict_origin'))
    no_rain_accuracy = (no_rain_correct / no_rain_count * 100) if no_rain_count > 0 else 0
    
    # Rainfall comparison - group by date
    rainfall_data = {}
    for p in predictions:
        predicted_at = p.get('predicted_at') or p.get('predictedAt')
        if predicted_at:
            if predicted_at.tzinfo is None:
                predicted_at = pytz.utc.localize(predicted_at)
            vn_time = predicted_at.astimezone(VN_TZ)
            date_key = vn_time.strftime('%Y-%m-%d')
            
            if date_key not in rainfall_data:
                rainfall_data[date_key] = {
                    'actual': [],
                    'predicted': []
                }
            
            actual = float(p.get('precip_mm_origin') or p.get('precipMM_origin') or 0)
            predicted = float(p.get('rain_prediction') or 0)
            
            rainfall_data[date_key]['actual'].append(actual)
            rainfall_data[date_key]['predicted'].append(predicted)
    
    # Calculate daily averages
    rainfall_comparison = []
    for date_key in sorted(rainfall_data.keys()):
        data = rainfall_data[date_key]
        avg_actual = sum(data['actual']) / len(data['actual']) if data['actual'] else 0
        avg_predicted = sum(data['predicted']) / len(data['predicted']) if data['predicted'] else 0
        
        rainfall_comparison.append({
            'date': date_key,
            'actual': round(avg_actual, 2),
            'predicted': round(avg_predicted, 2)
        })
    
    # Feature impact analysis
    feature_impact = analyze_feature_impact(predictions)
    
    return jsonify({
        'total_predictions': total,
        'rain_count': rain_count,
        'no_rain_count': no_rain_count,
        'overall_accuracy': round(overall_accuracy, 2),
        'rain_accuracy': round(rain_accuracy, 2),
        'no_rain_accuracy': round(no_rain_accuracy, 2),
        'correct_predictions': correct,
        'incorrect_predictions': incorrect,
        'confusion_matrix': {
            'true_positive': true_positive,
            'false_positive': false_positive,
            'true_negative': true_negative,
            'false_negative': false_negative
        },
        'rainfall_comparison': rainfall_comparison,
        'feature_impact': feature_impact
    })

def analyze_feature_impact(predictions):
    """Analyze how different features impact prediction accuracy"""
    
    # Temperature ranges
    temp_ranges = {
        'low': {'range': '< 15°C', 'filter': lambda p: float(p.get('tempC', 0)) < 15, 'correct': 0, 'total': 0},
        'medium': {'range': '15-25°C', 'filter': lambda p: 15 <= float(p.get('tempC', 0)) <= 25, 'correct': 0, 'total': 0},
        'high': {'range': '> 25°C', 'filter': lambda p: float(p.get('tempC', 0)) > 25, 'correct': 0, 'total': 0}
    }
    
    # Humidity ranges
    humidity_ranges = {
        'low': {'range': '< 50%', 'filter': lambda p: float(p.get('humidity', 0)) < 50, 'correct': 0, 'total': 0},
        'medium': {'range': '50-70%', 'filter': lambda p: 50 <= float(p.get('humidity', 0)) <= 70, 'correct': 0, 'total': 0},
        'high': {'range': '> 70%', 'filter': lambda p: float(p.get('humidity', 0)) > 70, 'correct': 0, 'total': 0}
    }
    
    # Pressure ranges
    pressure_ranges = {
        'low': {'range': '< 1010', 'filter': lambda p: float(p.get('pressure', 0)) < 1010, 'correct': 0, 'total': 0},
        'medium': {'range': '1010-1020', 'filter': lambda p: 1010 <= float(p.get('pressure', 0)) <= 1020, 'correct': 0, 'total': 0},
        'high': {'range': '> 1020', 'filter': lambda p: float(p.get('pressure', 0)) > 1020, 'correct': 0, 'total': 0}
    }
    
    # Wind speed ranges
    wind_ranges = {
        'low': {'range': '< 10 km/h', 'filter': lambda p: float(p.get('windspeedKmph', 0)) < 10, 'correct': 0, 'total': 0},
        'medium': {'range': '10-20 km/h', 'filter': lambda p: 10 <= float(p.get('windspeedKmph', 0)) <= 20, 'correct': 0, 'total': 0},
        'high': {'range': '> 20 km/h', 'filter': lambda p: float(p.get('windspeedKmph', 0)) > 20, 'correct': 0, 'total': 0}
    }
    
    # Calculate accuracy for each range
    for pred in predictions:
        is_correct = pred.get('predict') == pred.get('predict_origin')
        
        try:
            # Temperature
            for key, range_data in temp_ranges.items():
                if range_data['filter'](pred):
                    range_data['total'] += 1
                    if is_correct:
                        range_data['correct'] += 1
            
            # Humidity
            for key, range_data in humidity_ranges.items():
                if range_data['filter'](pred):
                    range_data['total'] += 1
                    if is_correct:
                        range_data['correct'] += 1
            
            # Pressure
            for key, range_data in pressure_ranges.items():
                if range_data['filter'](pred):
                    range_data['total'] += 1
                    if is_correct:
                        range_data['correct'] += 1
            
            # Wind speed
            for key, range_data in wind_ranges.items():
                if range_data['filter'](pred):
                    range_data['total'] += 1
                    if is_correct:
                        range_data['correct'] += 1
        except (ValueError, TypeError, KeyError):
            continue
    
    # Calculate percentages
    def calc_accuracy(range_dict):
        result = {}
        for key, data in range_dict.items():
            accuracy = (data['correct'] / data['total'] * 100) if data['total'] > 0 else 0
            result[data['range']] = {
                'accuracy': round(accuracy, 2),
                'count': data['total']
            }
        return result
    
    return {
        'temperature': calc_accuracy(temp_ranges),
        'humidity': calc_accuracy(humidity_ranges),
        'pressure': calc_accuracy(pressure_ranges),
        'wind_speed': calc_accuracy(wind_ranges)
    }

def get_data():
    # Get pagination parameters from query string
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    # Calculate skip
    skip = (page - 1) * per_page
    
    # Use cached/estimated count instead of exact count
    total_count = get_cached_count()
    rain_count = get_cached_rain_count()
    total_pages = (total_count + per_page - 1) // per_page
    
    # Fetch paginated data with PROJECTION (only needed fields)
    predicts = list(db.predict.find(
        {},
        {'_id': 1, 'predict': 1, 'predict_origin': 1, 'rain_prediction': 1, 
         'precip_mm_origin': 1, 'precipMM_origin': 1, 'predicted_at': 1}
    ).sort('predicted_at', DESCENDING).skip(skip).limit(per_page))
    
    result = []
    for predict in predicts:
        predict_dict = {}
        for key, value in predict.items():
            if isinstance(value, ObjectId):
                predict_dict[key] = str(value)
            elif isinstance(value, datetime.datetime):
                # Convert to Vietnam timezone
                if value.tzinfo is None:
                    value = pytz.utc.localize(value)
                vn_time = value.astimezone(VN_TZ)
                predict_dict[key] = vn_time.isoformat()
                predict_dict['date'] = vn_time.strftime('%d/%m/%Y')
                predict_dict['time'] = vn_time.strftime('%H:%M:%S')
            else:
                predict_dict[key] = value

        result.append(predict_dict)

    # Return prediction results with pagination metadata
    return jsonify({
        'data': result,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total_count': total_count,
            'rain_count': rain_count,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1
        }
    })