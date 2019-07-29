from threading import Thread

import slack
from flask import Blueprint, current_app

events = Blueprint("events", __name__, template_folder='templates')
events.config = {}


@events.record
def record_slack_config(setup_state):
    '''make a copy of relevant config upon blueprint register so we don't need to reference current_app'''
    events.config = {k: v for k, v in setup_state.app.config.get_namespace('COMPUTER_').items()}


from computer.slack.route import default_handler, register, EVENT_TYPES


def bg_slack(method=None, token=None, **kwargs):
    print(f'backgrounding task: method={method}, token={"<redacted>" if token else token}, kwargs={kwargs}')
    if not token:
        token = events.config['slack_oauth_access_token']

    def send_slack(token, **kwargs):
        slackclient = slack.WebClient(token=token)
        fun = getattr(slackclient, method)
        fun(**kwargs)

    thread = Thread(target=send_slack, daemon=True, kwargs={'token': token, **kwargs})
    thread.start()
    print('thread started')


def run_async(target, token=None, **kwargs):
    current_app.logger.trace(f'starting thread for {target} {kwargs}')
    if not token:
        token = events.config.get('slack_oauth_access_token')

    thread = Thread(target=target, daemon=True, kwargs={'token': token, **kwargs})
    thread.start()
    current_app.logger.trace('thread started')
    return thread