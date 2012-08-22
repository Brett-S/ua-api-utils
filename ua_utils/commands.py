import logging
import sys

import simplejson as json
import requests

logger = logging.getLogger('ua_utils.cli')
_commands = {}


def cmd(name=None):
    def wrap(f):
        if name is None:
            cmd_name = f.__name__
        else:
            cmd_name = name
        _commands[cmd_name] = f
        return f
    return wrap


def get_command(name):
    """Returns a command handler function or None if command isn't found"""
    return _commands.get(name)


@cmd('get-tokens')
def get_tokens(options):
    """Get all device tokens for an app"""
    logger.info('Retrieving device tokens and saving to %s' % options.outfile)
    resp = requests.get('https://go.urbanairship.com/api/device_tokens/',
                        params={'limit': 5},
                        auth=(options.app_key, options.secret))
    tokens = {
        'device_tokens_count': resp.json['device_tokens_count'],
        'active_device_tokens_count':
            resp.json['active_device_tokens_count'],
        'device_tokens': resp.json['device_tokens']
    }

    count = len(tokens['device_tokens'])
    total = tokens['device_tokens_count']

    while resp.json.get('next_page'):
        logger.info('Retrieved %d of %d' % (count, total))
        resp = requests.get(resp.json['next_page'],
                            auth=(options.app_key, options.secret))
        count = len(tokens['device_tokens'])
        tokens['device_tokens'].extend(resp.json['device_tokens'])

    logger.info('Done, saving to %s' % (options.outfile or '-'))
    if not options.outfile or options.outfile == '-':
        f = sys.stdout
    else:
        f = open(options.outfile, 'w')
    json.dump(tokens, f, indent='    ')


def tally_active_apids(apid_json):
    """Get tally for active apids"""
    active = 0
    for apid_data in apid_json:
        if apid_data['active'] is True:
            active += 1
    return active


@cmd('get-apids')
def get_apids(options):
    """Get all apids for an app"""
    logger.info('Retrieving apids and saving to %s' % options.outfile)
    resp = requests.get('https://go.urbanairship.com/api/apids/',
                       params={'limit': 5},
                       auth=(options.app_key, options.secret))
    apids = {'apids': resp.json['apids'], 'active_apids': 0}
    apids['active_apids'] = tally_active_apids(resp.json['apids'])

    count = len(apids['apids'])
    logger.info('Retrieved %d apids' % count)

    while resp.json.get('next_page'):
        resp = requests.get(resp.json['next_page'],
                            auth=(options.app_key, options.secret))
        apids['apids'].extend(resp.json['apids'])
        count = len(apids['apids'])
        logger.info('Retrieved %d apids' % count)
        apids['active_apids'] += tally_active_apids(resp.json['apids'])
    logger.info('Done, saving to %s' % (options.outfile or '-'))
    if not options.outfile or options.outfile == '-':
        f = sys.stdout
    else:
        f = open(options.outfile, 'w')
    json.dump(apids, f, indent='    ')


def get_unique_users(user_json, user_ids):
    """Get unique user_ids"""
    ids = [u_id for u_id in user_json if u_id['user_id'] not in
           user_ids]
    return ids


@cmd('get-users')
def get_users(options):
    """Get all users for an app"""
    logger.info('Retrieving user_ids and saving to %s' % options.outfile)
    index = 0
    increment = 10
    url = 'https://go.urbanairship.com/api/users/%d/%d' % (index, increment)
    resp = requests.get(url, auth=(options.app_key, options.secret))
    unique_users = resp.json['users']
    users = unique_users
    user_ids = [u_id['user_id'] for u_id in users]

    unique_count = len(user_ids)
    logger.info('Retrieved %d unique users' % unique_count)

    while unique_users:
        index += increment
        url = ('https://go.urbanairship.com/api/users/%d/%d' %
               (index, increment))
        resp = requests.get(url, auth=(options.app_key, options.secret))
        # So unfortunately this endpoint doesn't act consistently upon
        # reaching the "end" of the user_ids associated with the app.
        # This means we have to check against the full list of user_ids
        unique_users = get_unique_users(resp.json['users'], user_ids)
        users.extend(unique_users)
        user_ids.extend([u_id['user_id'] for u_id in unique_users])
        user_ids_count = len(user_ids)
        unique_count = len(unique_users)
        logger.info('Retrieved %d unique users for a total of %d users' %
                    (unique_count, user_ids_count))
    users_data = {'users': users}
    logger.info('Done, saving to %s' % (options.outfile or '-'))
    if not options.outfile or options.outfile == '-':
        f = sys.stdout
    else:
        f = open(options.outfile, 'w')
    json.dump(users_data, f, indent='    ')
