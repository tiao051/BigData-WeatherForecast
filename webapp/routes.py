from flask import Blueprint, send_from_directory
import os

from app.controllers.home_controller import home, get_data, statistics, get_statistics, get_error_clusters

main = Blueprint('main', __name__)

@main.route('/', methods=['GET'])
def home_route():
    return home()

@main.route('/get-data', methods=['GET'])
def get_data_route():
    return get_data()

@main.route('/statistics', methods=['GET'])
def statistics_route():
    return statistics()

@main.route('/api/statistics', methods=['GET'])
def api_statistics_route():
    return get_statistics()

@main.route('/api/error-clusters', methods=['GET'])
def api_error_clusters_route():
    return get_error_clusters()
