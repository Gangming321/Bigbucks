from flask import Flask, Blueprint, render_template, session, jsonify, flash, redirect, url_for
from flask_crontab import Crontab
from __init__ import app



bp = Blueprint('refresh', __name__, url_prefix='/refresh')

crontab = Crontab(app)