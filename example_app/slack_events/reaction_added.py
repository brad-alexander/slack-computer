from flask import request

from computer.slack import events, bg_slack
from computer.slack.route import register


@register('reaction_added')
def handle_reaction_added():
    if request.json['event']['reaction'] == 'plus2':
        bg_slack('reactions_add', token=events.config.get('slack_bot_token'),
                 name='shipitparrot',
                 channel=request.json['event']['item']['channel'],
                 timestamp=request.json['event']['item']['ts'])
    return 'ok'
