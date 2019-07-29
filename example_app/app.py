from logging.config import dictConfig

from flask import Flask

from computer import events
import example_app.slack_events.link_shared
import example_app.slack_events.message
import example_app.slack_events.reaction_added

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
