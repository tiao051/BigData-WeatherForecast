from flask import Blueprint, send_from_directory
import os

from app.controllers.home_controller import *

main = Blueprint('main', __name__)

@main.route('/', methods=['GET'])
def home_route():
    return home()

@main.route('/get-data', methods=['GET'])
def get_data_route():
    return get_data()

@main.route('/<path:undefined_path>', methods=['GET'])
def notfound_route(undefined_path):
    return notfound()