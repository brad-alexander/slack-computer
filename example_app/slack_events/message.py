from flask import request, current_app

from computer.slack import events, register, bg_slack

MESSAGE_SUBTYPES = [
    None,                   # No subtype
    "bot_message",          # A message was posted by an integration
    "channel_archive",      # A channel was archived
    "channel_join",         # A member joined a channel
    "channel_leave",        # A member left a channel
    "channel_name",         # A channel was renamed
    "channel_purpose",      # A channel purpose was updated
    "channel_topic",        # A channel topic was updated
    "channel_unarchive",    # A channel was unarchived
    "ekm_access_denied",    # Message content redacted due to Enterprise Key Management (EKM)
    "file_comment",         # A comment was added to a file
    "file_mention",         # A file was mentioned in a channel
    "file_share",           # A file was shared into a channel
    "group_archive",        # A group was archived
    "group_join",           # A member joined a group
    "group_leave",          # A member left a group
    "group_name",           # A group was renamed
    "group_purpose",        # A group purpose was updated
    "group_topic",          # A group topic was updated
    "group_unarchive",      # A group was unarchived
    "me_message",           # A /me message was sent
    "message_changed",      # A message was changed
    "message_deleted",      # A message was deleted
    "message_replied",      # A message thread received a reply
    "pinned_item",          # An item was pinned in a channel
    "thread_broadcast",     # A message thread's reply was broadcast to a channel
    "unpinned_item",        # An item was unpinned from a channel
]

message_dispatch = {subtype: [] for subtype in MESSAGE_SUBTYPES}


def register_subtype(subtype, *predicates):
    def decorator(f):
        message_dispatch[subtype].insert(0, (f, predicates))
        return f
    return decorator


@register_subtype('me_message', 'request.json["event"]["user"] == "UCXXXXXK"')
def handle_me_message():
    bg_slack('reactions_add', token=events.config.get('slack_bot_token'),
             name='blog',
             channel=request.json['event']['channel'],
             timestamp=request.json['event']['ts'])
    return 'ok'


@register_subtype('channel_purpose')
def handle_channel_purpose():
    print('PURPOSE!!!!!!!!')
    return 'ok'


@register_subtype(None,
                  *[f"'{word}' in request.json['event']['text'].lower()"
                    for word in ['tea', 'earl']]
                  + ["'hot' not in request.json['event']['text'].lower()"])
def handle_tea_earl_gray_not():
    bg_slack('chat_postMessage', token=events.config.get('slack_bot_token'),
             text='https://www.youtube.com/watch?v=eVUuaDXBhs4',
             channel=request.json['event']['channel'],
             )


@register_subtype(None,
                  *[f"'{word}' in request.json['event']['text'].lower()"
                    for word in ['tea', 'earl', 'hot']])
def handle_tea_earl_gray_hot():
    bg_slack('chat_postMessage', token=events.config.get('slack_bot_token'),
             text='https://i.imgur.com/kGypM2u.jpg',
             channel=request.json['event']['channel'],
             )


@register('message')
def handle_message():
    subtype = request.json['event'].get('subtype')
    for handler, predicates in message_dispatch.get(subtype):
        if all(eval(predicate) for predicate in predicates):
            current_app.logger.debug(f'subtype handlers run for {subtype}: {handler}')
            result = handler()
            if result is False:
                continue
            else:
                break
    else:
        current_app.logger.debug(f'no subtype handlers run for {subtype}')
    return 'ok'