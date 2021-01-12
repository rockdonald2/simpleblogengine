from blogengine import cache, API_URL

from flask import session
import requests
from anytree import AnyNode, LevelOrderIter, importer


def human_format(num):
    """
    A function that converts a number into a humanly readable format.
    """

    num = float('{:.3g}'.format(num))
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    return '{}{}'.format('{:f}'.format(num).rstrip('0').rstrip('.'), ['', 'K', 'M', 'B', 'T'][magnitude])


# * cache each opened post for 2 minutes
# * cache only works for unlogged users, for logged in users the caching mechanism is bypassed
def check_login():
    """ 
    Checks whether the user is logged in or not.
    Returns True, otherwise False.
    """
    return 'auth' in session


# * Cache current posts for 2 minutes
# * This also results in new posts not appearing for 2 minutes after publishing
@cache.cached(timeout=120, key_prefix='all_posts', unless=check_login)
def get_all_posts():
    posts = requests.get(API_URL + 'posts?projection={"title": 1, "date": 1, "author": 1}&sort=[("date", -1)]').json()['_items']
    return posts


def childs_are_deleted(pc):
    """ 
    Checks whether a specific parent comment's/reply's child replies are deleted or not.
    Returns True if they are, otherwise False.
    """

    # if this array is empty after the iteration, then all of the leafs are deleted
    check_arr = [reply.data['reply_id'] for reply in LevelOrderIter(pc, filter_= lambda reply: 'reply_id' in reply.data and not reply.data['deleted'] and reply != pc)]

    return len(check_arr) == 0


def deep_check_comments(pc):
    """ 
    Checks whether a specific parent comment's child replies are deleted.
    The pc argument has to be a root element.
    If the arguments isn't a root element, then it always returns False
    Returns True if they are, otherwise False.
    """

    if pc.is_root:
        return pc.data['deleted'] and childs_are_deleted(pc)
    else:
        return False


def make_deep_check():
    """ 
    This function has to be called to perform a deep check on comments.
    This function checks all of the comments from the database, regardless the posts. 
    """

    comments = requests.get(API_URL + 'comments/').json()['_items']

    for c in comments:
        # * If the whole tree is deleted, than delete from the database
        # * Otherwise do nothing
        if deep_check_comments(importer.import_({
            'data': c['data'],
            'post_id': c['post_id'],
            'children': c['children']
        })):
            resp = requests.delete(API_URL + 'comments/' + c['_id'], headers={"If-Match": c['_etag']})

# ! Now it is left off, which means each time the server is restarted, and first run, the function would be called if left on
""" make_deep_check() """