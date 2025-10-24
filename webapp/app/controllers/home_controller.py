from flask import render_template, jsonify, request
from bson import ObjectId
import datetime
from pymongo import DESCENDING
from database.mongodb import db

def home():
    # Initial page load - fetch first page
    page = 1
    per_page = 50
    skip = (page - 1) * per_page
    
    predicts = list(db.predict.find().sort('predicted_at', DESCENDING).skip(skip).limit(per_page))
    total_count = db.predict.count_documents({})
    total_pages = (total_count + per_page - 1) // per_page  # Ceiling division

    for predict in predicts:
        predicted_at = predict.get('predictedAt') or predict.get('predicted_at')
        if predicted_at:
            predict['date'] = predicted_at.strftime('%d/%m/%Y')
            predict['time'] = predicted_at.strftime('%H:%M:%S')

    return render_template('home.html', predicts=predicts, total_count=total_count, total_pages=total_pages, current_page=page, per_page=per_page)

def get_data():
    # Get pagination parameters from query string
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    # Calculate skip
    skip = (page - 1) * per_page
    
    # Get total count for pagination info
    total_count = db.predict.count_documents({})
    total_pages = (total_count + per_page - 1) // per_page
    
    # Fetch paginated data
    predicts = list(db.predict.find().sort('predicted_at', DESCENDING).skip(skip).limit(per_page))
    
    result = []
    for predict in predicts:
        predict_dict = {}
        for key, value in predict.items():
            if isinstance(value, ObjectId):
                predict_dict[key] = str(value)
            elif isinstance(value, datetime.datetime):
                predict_dict[key] = value.isoformat()
                predict_dict['date'] = value.strftime('%d/%m/%Y')
                predict_dict['time'] = value.strftime('%H:%M:%S')
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
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1
        }
    })