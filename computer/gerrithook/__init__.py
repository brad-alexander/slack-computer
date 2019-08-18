import json
from urllib.parse import urlparse, parse_qs
from pprint import pprint

import slack

from flask import Blueprint, current_app, request, g, jsonify

bp = Blueprint("gerrithook", __name__, template_folder='templates')
bp.config = {}


class SlackError(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv


@bp.record
def record_config(setup_state):
    """make a copy of relevant config upon blueprint register so we don't need to reference current_app"""
    bp.config = {k: v for k, v in setup_state.app.config.get_namespace('POKER_').items()}


@bp.route('/', methods=['POST'])
def hook():
    current_app.logger.debug(request.json)
    return 'ok'