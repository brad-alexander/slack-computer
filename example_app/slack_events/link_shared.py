import json

from pathlib import PurePosixPath
from urllib.parse import unquote, urlparse

import slack
import requests

from flask import request
from computer.slack import events, register, bg_slack, run_async


def get_user(token, email):
    return slack.WebClient(token).users_lookupByEmail(email=email)['user']


def get_user_img(user):
    return user['profile']['image_32']


def format_changedata(token, changedata):
    blocks = [{"type": "section",
               "text": {"type": "mrkdwn",
                        "text": f"{changedata['subject'][:300]}\n*project*: {changedata['project']} *status:* :{changedata['status']}: {changedata['status']}\n"}
               }]
    owner = changedata['owner']
    ownerelements = [{"type": "mrkdwn", "text": f"*Owner:*"}]
    ownerimage = get_user_img(get_user(token, owner['email']))
    ownerimageelement = {"type":      "image",
                         "image_url": ownerimage,
                         "alt_text":  owner['email']}
    ownerelements.append(ownerimageelement)

    ownertext = {"type": "mrkdwn", "text": f"{owner['name']}"}
    ownerelements.append(ownertext)

    blocks.append(dict(type='context', elements=ownerelements))

    reviewerelements = [{"type": "mrkdwn", "text": f"*Reviewers:*"}]
    reviewers = [reviewer for reviewer in changedata['reviewers'].get('REVIEWER', []) if reviewer.get('email')]
    for reviewer in reviewers:
        reviewerimage = get_user_img(get_user(token, reviewer['email']))
        reviewerimageelement = {"type": "image",
                                "image_url": reviewerimage,
                                "alt_text": reviewer['email']}
        reviewerelements.append(reviewerimageelement)
        reviewertext = {"type": "mrkdwn", "text": f"{reviewer['username']}\n"}
        reviewerelements.append(reviewertext)
    blocks.append(dict(type='context', elements=reviewerelements))
    attachment = {"blocks": blocks}
    return attachment


def send_unfurl(links, token, channel, ts):
    unfurls = {link['url']: get_changedata(link) for link in links if link['domain'] == events.config['gerrit_domain']}
    unfurls = {k: format_changedata(token, v) for k, v in unfurls.items() if v is not None}
    if unfurls:
        return bg_slack('chat_unfurl', token=token, channel=channel, ts=ts, unfurls=unfurls)
    else:
        print('no unfurls')


def remove_csrf_line(text):
    return '\n'.join(text.splitlines()[1:])


def path_parts(url):
    path = url
    path = urlparse(path)
    path = path.path + path.fragment
    path = unquote(path)
    path = PurePosixPath(path)
    return path.parts


def get_changedata(link):
    """# curl https://gerrit.example.com/changes/8675309
        )]}'
        {
          "id": "XXXXXXXXXXX~I8a2596ea02bf4001b14dd74f28378fc4a0",
          "project": "XXX/XXXXXXX",
          "branch": "master",
          "hashtags": [],
          "change_id": "I8a2596ea02bf4001b14dd74f28378fc4a0",
          "subject": "change stuff",
          "status": "MERGED",
          "created": "2019-07-26 21:06:00.453000000",
          "updated": "2019-07-26 21:21:28.542000000",
          "submitted": "2019-07-26 21:18:17.140000000",
          "insertions": 1,
          "deletions": 1,
          "unresolved_comment_count": 0,
          "_number": 8675309,
          "owner": {
            "_account_id": 1000042
          }
        }
    """
    for part in path_parts(link['url']):
        if part.isdigit():
            try:
                url = f'https://{events.config["gerrit_domain"]}/changes/{part}/detail'
                resp = requests.get(url)
                resp.raise_for_status()
                print(resp.text)
                text = remove_csrf_line(resp.text)
                changedata = json.loads(text)
                return changedata
            except requests.HTTPError as e:
                print(f'HTTPError {e} on {part}')
                continue


def gen_unfurl(link):
    if link['domain'] == events.config["gerrit_domain"]:
        pass
    return {
        "text": f"the link {link['url']}"
    }


@register('link_shared')
def handle_link_shared():
    """{'type': 'event_callback',
        'event':
            {'type': 'link_shared',
            'user': 'UXXXXXXK',
            'channel': 'CCXXXXXXXB',
            'message_ts': '1564217720.000000',
            'links':
                [{'url': 'http://computer.example.com/1234', 'domain': 'computer.example.com'}]},
        'token': '', 'team_id': 'TCXXXXXY', 'api_app_id': 'ALXXXXXB', 'event_id': 'EvXXXXXXX7',
        'event_time': 1564217720, 'authed_users': ['UXXXXXXK'], }
    """
    links = request.json['event']['links']
    if events.config['gerrit_domain'] in [link['domain'] for link in links]:
        run_async(send_unfurl, links=links, token=events.config['slack_oauth_access_token'],
                  channel=request.json['event']['channel'], ts=request.json['event']['message_ts'])
    else:
        bg_slack('chat_unfurl', token=events.config['slack_oauth_access_token'],
                 channel=request.json['event']['channel'],
                 ts=request.json['event']['message_ts'],
                 unfurls={link['url']: gen_unfurl(link) for link in request.json['event']['links']})

    return 'ok'


