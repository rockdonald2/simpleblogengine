from flask import Flask
from flask_caching import Cache
from flask_misaka import Misaka
from json import load
from os import urandom
from datetime import timedelta

with open('blogengine/config.json', 'r') as config_file:
    config_json = load(config_file)

    SECRET_KEY = config_json['SECRET_KEY']
    API_URL = config_json['API_URL'] # * The API can be reached with this endpoint
    WEBSITE_DOMAIN = config_json['WEBSITE_DOMAIN']

# * Starting flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=2)
# * cache-control
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 20
app.config['CACHE_TYPE'] = 'simple'
app.config['CACHE_DEFAULT_TIMEOUT'] = 300
cache = Cache(app)
markdown = Misaka(app, fenced_code=True, underline=True, highlight=True, quote=True, math=True, math_explicit=True, strikethrough=True, superscript=True, escape=True, smartypants=True)
# * Cache is only cleared when there's a new comment/deleted comment/deleted post
# * Cache only works for unlogged users

from blogengine import routes