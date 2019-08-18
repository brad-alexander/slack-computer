"""
Slack planning poker

Flow:
 * -> "message_action" "Estimate"
   -> app creates interactive message
   -> 0-n people vote using interactive message buttons
   -> Votes are closed, scores shown
   -> *
"""
import json
from urllib.parse import urlparse, parse_qs
from pprint import pprint

import slack

from flask import Blueprint, current_app, request, g, jsonify

bp = Blueprint("poker", __name__, template_folder='templates')
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


@bp.before_request
def verify_token():
    current_app.logger.debug(f'verifying token')
    g.data = request.json or json.loads(request.form['payload'])
    current_app.logger.debug(f'data: {g.data}')
    presented_token = g.data.get('token', None)
    configured_token = bp.config['slack_token']
    if presented_token is None:
        current_app.logger.debug(f'verifying token')
        raise SlackError('token required', status_code=401)
    elif presented_token == configured_token:
        current_app.logger.debug(f'token verified')
        g.authenticated = True
    else:
        current_app.logger.debug(
            f'provided token {presented_token} does not match configured token {configured_token[:5]}...')
        raise SlackError('token provided does not match configured SLACK_TOKEN',
                         status_code=403)


@bp.route('/options', methods=['GET', 'POST'])
def options():
    current_app.logger.debug(request.form)
    return 'ok'


def get_user_img_by_id(userid):
    return slack.WebClient(bp.config['slack_oauth_access_token']).users_info(user=userid)['user']['profile']['image_32']


class VoteURL:
    def __init__(self, userid, vote, image=None):
        if isinstance(userid, list):
            raise ValueError
        self.userid = userid
        self.vote = vote
        self._image = image

    def __str__(self):
        return self.image

    def __repr__(self):
        return str(self)

    @classmethod
    def from_url(cls, url):
        parts = urlparse(url)
        query = parse_qs(parts.query)
        return cls(query['user'][0], query['vote'][0])

    @property
    def image(self):
        if not self._image:
            self._image = get_user_img_by_id(self.userid) + f'?vote={self.vote}&user={self.userid}'
        return self._image

    @property
    def context(self):
        return dict(type="image", image_url=self.image, alt_text=repr(self))

    @property
    def revealed_context(self):
        return [dict(type="image", image_url=self.image, alt_text=repr(self)),
                dict(type="mrkdwn", text=f":{self.vote} ")]


class VoteURLs:
    def __init__(self, votes=None):
        self._votes = votes

    def __str__(self):
        return repr(self._votes)

    def __iter__(self):
        return iter(self._votes)

    def __len__(self):
        return len(self.to_dict())

    def __contains__(self, key):
        return key in self.to_dict()

    @classmethod
    def from_blocks(cls, blocks):
        for block in blocks:
            if block['block_id'] == 'votes':
                votes = block
                break
        else:
            return cls(votes=[])
        voteurls = []
        for vote in votes['elements']:
            if vote['type'] == 'image':
                voteurls.append(VoteURL.from_url(vote['image_url']))
        return cls(votes=voteurls)

    def to_dict(self):
        return {v.userid: v for v in self._votes}

    def to_blocks(self, revealed=False):
        for k, v in self.to_dict().items():
            if revealed:
                yield from v.revealed_context
            else:
                yield v.context


@bp.route('/action', methods=['GET', 'POST'])
def action():
    current_app.logger.debug(request.form)
    current_app.logger.debug(g.data)
    if g.data['type'] == 'block_actions':
        current_app.logger.debug(g.data.keys())
        blocks = g.data['message']['blocks']
        user = g.data['user']
        vote_value = [x['value'].split('_')[1] for x in g.data['actions']][0]
        reveal = 'reveal' in vote_value
        vote = VoteURL(user['id'], vote_value)
        voteurls = VoteURLs.from_blocks(blocks)
        for v in voteurls:
            current_app.logger.debug(v)
        if not reveal:
            voteurls._votes.append(vote)
        current_app.logger.debug(blocks)
        voted = blocks[1]
        num_votes = len(voteurls)
        new_elements = voted['elements'][0:1]
        new_elements[0]['text'] = f'Votes: {num_votes}'
        new_elements.extend(voteurls.to_blocks(revealed=reveal))
        voted['elements'] = new_elements
        if reveal:
            blocks = blocks[0:2]
        pprint(blocks)
        slack.WebClient(token=bp.config['slack_oauth_access_token']) \
            .chat_update(text=g.data['message']['text'] + 'New Text!', blocks=blocks, channel=g.data['channel']['id'],
                         ts=
                         g.data['message']['ts'])
    elif g.data['type'] == 'message_action' and g.data['callback_id'] == 'estimate':
        msg = g.data['message']
        buttons = [{'type': "button",
                    'text': dict(type="plain_text",
                                 text=str(num),
                                 emoji=True),
                    'value': f"vote_{num}"}
                           for num in [0, 1, 2, 3, 5, 8, 13, 21, 34]]
        buttons.append({'type': "button",
                    'text': dict(type="plain_text",
                                 text=':skull_and_crossbones:Close Voting:skull_and_crossbones:',
                                 emoji=True),
                    'value': f"vote_reveal",
                    "style": "danger"})
        blocks = [{
            "type":     "section",
            "block_id": "section789",
            "fields":   [{
                "type": "mrkdwn",
                "text": '*Estimate:* ' + msg['text']
            }]
        },
            {
                "type":     "context",
                "block_id": "votes",
                "elements": [{
                    "type": "mrkdwn",
                    "text": "Votes: 0"
                }]
            },
            dict(type="actions",
                 elements=buttons)]
        outmessage = dict(text=msg['text'], blocks=blocks, channel=g.data['channel']['id'])
        current_app.logger.debug(outmessage)
        slack.WebClient(token=bp.config['slack_oauth_access_token']).chat_postMessage(**outmessage)
    return 'ok'
