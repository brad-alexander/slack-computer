from logging.config import dictConfig

from flask import Flask

from computer import events
from slack_events import link_shared
from slack_events import message
from slack_events import reaction_added

dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s %(funcName)s:%(lineno)d : %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})


def create_app():
    app = Flask(__name__)
    app.config.from_pyfile('./config.py')
    app.register_blueprint(events)
    return app


app = create_app()
if app.config['DEBUG']:
    app.logger.setLevel('TRACE')
