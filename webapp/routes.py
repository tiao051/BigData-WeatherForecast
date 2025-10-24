from flask import Blueprint, send_from_directory
import os

from app.controllers.home_controller import home, get_data

main = Blueprint('main', __name__)

@main.route('/', methods=['GET'])
def home_route():
    return home()

@main.route('/get-data', methods=['GET'])
def get_data_route():
    return get_data()
