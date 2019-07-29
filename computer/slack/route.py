from flask import current_app, jsonify, request, g

from computer.slack import events
from computer.slack.util import SlackError

EVENT_TYPES = [
    "app_home_opened",
    "app_mention",
    "app_rate_limited",
    "app_uninstalled",
    "channel_archive",
    "channel_created",
    "channel_deleted",
    "channel_history_changed",
    "channel_left",
    "channel_rename",
    "channel_unarchive",
    "dnd_updated",
    "dnd_updated_user",
    "email_domain_changed",
    "emoji_changed",
    "file_change",
    "file_comment_added",
    "file_comment_deleted",
    "file_comment_edited",
    "file_created",
    "file_deleted",
    "file_public",
    "file_shared",
    "file_unshared",
    "grid_migration_finished",
    "grid_migration_started",
    "group_archive",
    "group_close",
    "group_deleted",
    "group_history_changed",
    "group_left",
    "group_open",
    "group_rename",
    "group_unarchive",
    "im_close",
    "im_created",
    "im_history_changed",
    "im_open",
    "link_shared",
    "member_joined_channel",
    "member_left_channel",
    "message",
    "message.app_home",
    "message.channels",
    "message.groups",
    "message.im",
    "message.mpim",
    "pin_added",
    "pin_removed",
    "reaction_added",
    "reaction_removed",
    "resources_added",
    "resources_removed",
    "scope_denied",
    "scope_granted",
    "star_added",
    "star_removed",
    "subteam_created",
    "subteam_members_changed",
    "subteam_self_added",
    "subteam_self_removed",
    "subteam_updated",
    "team_domain_change",
    "team_join",
    "team_rename",
    "tokens_revoked",
    "url_verification",
    "user_change",
    "user_resource_denied",
    "user_resource_granted",
    "user_resource_removed",
]


def default_handler():
    return 'ok'


dispatch = {event_type: default_handler for event_type in EVENT_TYPES}


@events.errorhandler(SlackError)
def handle_verification_error(error):
    current_app.logger.debug(f'handling error {error}')
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


@events.before_request
def verify_token():
    current_app.logger.trace(f'verifying token')
    presented_token = request.json.get('token', None)
    configured_token = events.config['slack_token']
    if presented_token is None:
        current_app.logger.trace(f'verifying token')
        raise SlackError('token required', status_code=401)
    elif presented_token == configured_token:
        current_app.logger.trace(f'token verified')
        g.authenticated = True
    else:
        current_app.logger.trace(f'provided token {presented_token} does not match configured token {configured_token[:5]}...')
        raise SlackError('token provided does not match configured SLACK_TOKEN',
                         status_code=403)


def register(event_type):
    if event_type not in EVENT_TYPES:
        raise KeyError('{} not a valid event type'.format(event_type))

    def decorator(f):
        dispatch[event_type] = f
        return f
    return decorator


@register('url_verification')
def handle_url_verification():
    current_app.logger.debug(f'handling verification')
    return request.json['challenge']


@events.route('/', methods=['GET', 'POST'])
def root():
    if request.json is None:
        raise SlackError('Expecting JSON post', status_code=400)
    current_app.logger.debug(f'handling {request} {request.json}')
    if not g.authenticated:
        abort(403) # verify_token()
    json = request.json or {}
    event_type = json['type'] \
        if json['type'] == 'url_verification' \
        else json['event']['type']
    current_app.logger.trace(f'detected event_type as {event_type}')
    handler = dispatch.get(event_type, None)
    current_app.logger.debug(f'handling {event_type} via {handler}')
    if handler is None:
        raise SlackError('ok', status_code=200)
    result = handler()
    current_app.logger.trace(f'result is {result}')

    return result

