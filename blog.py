from flask import Flask, request, url_for, redirect, session, abort
from flask_caching import Cache
from jinja2 import Environment, FileSystemLoader, select_autoescape, Markup
import requests
import markdown
import pymdownx
from bcrypt import hashpw, gensalt
from os import urandom
from datetime import datetime, timedelta
from re import fullmatch, compile
from json import dumps
from anytree import AnyNode, find, LevelOrderIter
from anytree.exporter import JsonExporter
from anytree.importer import DictImporter
import uuid

""" 
TODO: -
"""

""" 
! bug: if the whole comment tree is deleted, the comments still remain there
? we can solve this bug, by checking every time one parent is going to be deleted that whether the parent's children nodes are also deleted,
? if so, we can delete the whole tree
? A partial solution is the one mentioned above, a more thorough solution would be a deep check every time a comment is deleted
? But, it's widely unnecessary so to say, because it's very unlikely that a whole tree will be deleted
? The deep-check can be interchanged with a timed deep-check, made possible with a function call
"""

# * Starting flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = urandom(16)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=2)
# * cache-control
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 20
app.config['CACHE_TYPE'] = 'simple'
app.config['CACHE_DEFAULT_TIMEOUT'] = 300
cache = Cache(app)
# * Cache is only cleared when there's a new comment/deleted comment/deleted post

# * The API can be reached with this endpoint
API_URL = 'http://127.0.0.1:5000/api/'

# * tree exporter to JSON
exporter = JsonExporter()
# * tree importer to Dict
importer = DictImporter()

# * Environment used in JINJA2 templates
env = Environment(
    loader=FileSystemLoader('templates/'),
    autoescape=select_autoescape(['html'])
)

# * Extensions for the markdown JINJA2 filter
extension_configs = {
    "pymdownx.highlight": {
        "guess_lang": True,
        "use_pygments": True,
        "noclasses": True,
        "linenums": False
    }
}
extensions = ['meta', 'attr_list', 'wikilinks', 'pymdownx.extra', 'admonition', 'smarty', 'nl2br', 'sane_lists', 'pymdownx.betterem', 'pymdownx.caret', 'pymdownx.critic', 'pymdownx.emoji', 'pymdownx.highlight', 'pymdownx.magiclink', 'pymdownx.mark', 'pymdownx.saneheaders', 'pymdownx.superfences', 'pymdownx.tilde']
md = markdown.Markdown(extensions=extensions, extension_configs=extension_configs)
# * the markup constructor creates a safe text that can be inserted into HTML files
env.filters['markdown'] = lambda text: Markup(md.convert(text))
env.trim_blocks = True
env.lstrip_blocks = True


@app.errorhandler(404)
@app.errorhandler(405)
@app.errorhandler(500)
@app.errorhandler(403)
def error_handler(e):
    error_template = env.get_template('error.html')
    return error_template.render(title=str(e))


# * cache each opened post for 2 minutes
# * cache only works for unlogged users, for logged in users the caching mechanism is bypassed
def check_login():
    return 'auth' in session

# * Cache current posts for 2 minutes
# * This also results in new posts not appearing for 2 minutes after publishing
@cache.cached(timeout=120, key_prefix='all_posts', unless=check_login)
def get_all_posts():
    posts = requests.get(API_URL + 'posts?projection={"text": 0}').json()['_items']
    return posts


@app.route('/', methods=['GET'])
@app.route('/home', methods=['GET'])
@app.route('/search', methods=['GET', 'POST'])
def home():
    """
    Index route, where the page loads,
    can take in a message in the form of a query string.
    The posts are cached for 2 minutes after loading, for users that aren't logged in.
    """

    posts = None

    # * this form only appears if we access the route via search
    form = request.form
    if form:
        keywords = [Markup(word).striptags() for word in form['words'].split(' ') if len(word) >= 3]
        posts = get_all_posts()
        filtered_posts = []

        for p in posts:
            flag = True
            for k in keywords:
                if p['title'].find(k) == -1:
                    flag = False

                if not flag:
                    break

            if flag:
                filtered_posts.append(p)

        posts = filtered_posts
    else:
        posts = get_all_posts()

    posts.sort(key=lambda p: p['date'], reverse=True)

    home_template = env.get_template('home.html')
    message = eval(request.args.get('message')) if request.args.get('message') else None 
    return home_template.render(title='A Simple Blog Engine', posts=posts, session=session, message=message)
    

@app.route('/login', methods=['POST', 'GET'])
def login():
    """
    Login form where one user can log in, we cannot make users directly from the webpage, it is unnecessary,
    users are loaded from the mongoDB collection by a GET request.
    The logged in user is saved in session for 2 days.
    If a user refers to this page, after logging in, it automatically redirects the user to the home page,
    with a message
    """

    login_template = env.get_template('login.html')

    if 'auth' in session:
        return redirect(url_for('home', message={'category': 'gr', 'msg': 'You\'re already logged in!'}))
    elif request.method == 'GET':
        return login_template.render(title='Log into your account')
    elif request.method == 'POST':
        email = request.form['email']
        pwd = request.form['pwd']
       
        existing_user = requests.get(API_URL + 'users?where={"email":"' + email + '"}').json()['_items']
        if existing_user:
            if hashpw(pwd.encode('utf-8'), existing_user[0]['pwd'].encode('utf-8')) == existing_user[0]['pwd'].encode('utf-8'):
                session.permanent = True
                session['auth'] = (email, existing_user[0]['name'], existing_user[0]['writer'], existing_user[0]['_id'][14:])
                return redirect(url_for('home', message={'category': 'gr', 'msg': 'You\'ve successfully logged in!'}))

        return login_template.render(title='Log into your account', message={'category': 'err', 'msg': 'Invalid login credentials'})


def validate(p):
    """ 
    Validates the argument password to a regexp object, returns a Match object, or None
    """

    pwd_regexp = compile(r'^.*(?=.{8,})(?=.*[a-zA-Z])(?=.*?[A-Z])(?=.*\d)[a-zA-Z0-9!@£$%^&*()_+={}?:~\[\]]+$')
    return fullmatch(pwd_regexp, p)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Registers a new user, makes a post request to the users collection.
    """

    register_template = env.get_template('register.html')

    if 'auth' in session:
        return redirect(url_for('home', message={'category': 'gr', 'msg': 'Sign out first before registering a new account'}))
    elif request.method == 'GET':
        return register_template.render(title='Register your new account')
    elif request.method == 'POST':
        form = request.form

        if not validate(form['pwd']):
            return register_template.render(title='Register your account', message={'category': 'err', 'msg': 'Your password didn\'t match the requested format'})
        
        if not (form['pwd'] == form['cpwd']):
            return register_template.render(title='Register your account', message={'category': 'err', 'msg': 'Passwords do not match'})
        
        user = {
            'email': form['email'],
            'name': Markup(form['name']).striptags(),
            'pwd': hashpw(form['pwd'].encode('utf-8'), gensalt()),
            'writer': False
        }

        resp = requests.post(API_URL + 'users/', user)

        if resp.status_code != 201:
            return redirect(url_for('home', message={'category': 'err', 'msg': 'Something went wrong'}))

        return redirect(url_for('home', message={'category': 'gr', 'msg': 'You\'ve have successfully created your account'}))


@app.route('/logout', methods=['GET'])
def logout():
    """
    Logout logic, manually clears the session associated to the user,
    after logging out redirects the user to the home page with a message
    """

    session.pop('auth', None)
    return redirect(url_for('home', message={'category': 'gr', 'msg': 'You\'ve successfully logged out!'}))


@app.route('/post/<id>', methods=['GET'])
@cache.cached(timeout=120, unless=check_login)
def post(id):
    """ 
    This route displays one post, requested from the database with an ID associated to the post.
    Each id is unique.
    """

    post_template = env.get_template('post.html')
    p = requests.get(API_URL + 'posts/' + id)

    if p.status_code == 404:
        abort(404, "Post not found")
    else:
        p = p.json()

    comments = requests.get(API_URL + 'comments?where={"post_id":"' + id + '"}').json()['_items']

    comments.sort(reverse=True, key=lambda c: c['data']['vote'])

    return post_template.render(title=p['title'], post=p, session=session, id=id, comments=comments)


@app.route('/comment&<id>', methods=['GET', 'POST'])
def comment(id):
    """
    Allows the user to post comments, automatically makes a post request to the database.
    After the post refreshes the post uncached with new comments.
    """

    if 'auth' in session:
        if request.method == 'POST':
            form = request.form

            headers = {
                'Content-Type': 'application/json'
            }

            comment = {
                'author': session['auth'][1],
                'text': Markup(form['cm']).striptags(),
                'date': datetime.today().strftime('%Y.%m.%d - %H:%M')
            }
            
            resp = requests.post(API_URL + 'comments/', exporter.export(AnyNode(data=comment, post_id=id)), headers=headers)

            if resp.status_code != 201:
                return redirect(url_for('home', message={'category': 'err', 'msg': 'Something went wrong'}))

        cache.clear()
        return redirect(url_for('post', id=id))
    else:
        return redirect(url_for('home', message={'category': 'err', 'msg': 'You\'re not logged in to comment on this post'}))


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
            
# ! Now it is left on, which means each time the server is restarted, and first run, the function is called
make_deep_check()


@app.route('/comment/delete&<id>', methods=['POST'])
def comment_delete(id):
    """
    Deletes a comment. Only two users can delete the comment, the author of the comment and the writer of the post.
    The delete functionality is variable.
    If the comment has no replies, it is deleted entirely, even from the database.
    Although, if the comment has replies, it remains unchanged, only its text changes.
    """

    cid = id[:24]
    sid = id[24:] or None

    if 'auth' in session:
        cm = requests.get(API_URL + 'comments/' + cid).json()
        postAuthor = requests.get(API_URL + 'posts/' + cm['post_id']).json()['author']

        headers = {
            "If-Match": cm['_etag'],
            "Content-Type": "application/json"
        }

        relevant = {
            'data': cm['data'],
            'post_id': cm['post_id'],
            'children': cm['children']
        }

        if sid == None:
            # * Post is a comment
            if session['auth'][1] == cm['data']['author'] or session['auth'][1] == postAuthor:
                # * Has no child replies
                if not cm['children']:
                    resp = requests.delete(API_URL + 'comments/' + cid, headers=headers)

                    if resp.status_code != 204:
                        return redirect(url_for('home', message={'category': 'err', 'msg': 'Something went wrong'}))
                # * Has child replies
                else:
                    # * Check whether all of its child replies are deleted or not
                    resp = None
                    
                    parentComment = importer.import_(relevant)

                    # * If they are, then delete the whole tree
                    if childs_are_deleted(parentComment):
                        resp = requests.delete(API_URL + 'comments/' + cid, headers=headers)
                    # * If not, then only change the comments text to deleted
                    else:
                        edit = {
                            'data': {
                                'text': 'This comment was deleted',
                                'deleted': True
                            }
                        }

                        resp = requests.patch(API_URL + 'comments/' + cid, dumps(edit), headers=headers)

                    if resp.status_code != 200 and resp.status_code != 204:
                        return redirect(url_for('home', message={'category': 'err', 'msg': 'Something went wrong'}))
            else:
                return redirect(url_for('home', message={'category': 'err', 'msg': 'You\'re not allowed to do that'}))
        else:
            # * Post is a reply

            parentComment = importer.import_(relevant)
            searchedReply = find(parentComment, lambda reply: 'reply_id' in reply.data and reply.data['reply_id'] == id)

            if session['auth'][1] == searchedReply.data['author'] or session['auth'][1] == postAuthor:
                resp = None

                if searchedReply.children and not childs_are_deleted(searchedReply):
                    searchedReply.data['text'] = 'This comment was deleted'
                    searchedReply.data['deleted'] = True
                    resp = requests.patch(API_URL + 'comments/' + cid, exporter.export(parentComment), headers=headers)
                else:
                    searchedParent = searchedReply.parent
                    searchedParent.children = tuple(filter(lambda reply: reply.data['reply_id'] != id, searchedParent.children))
                    resp = requests.put(API_URL + 'comments/' + cid, exporter.export(parentComment), headers=headers)

                if resp.status_code != 200:
                    return redirect(url_for('home', message={'category': 'err', 'msg': 'Something went wrong'}))
            else:
                return redirect(url_for('home', message={'category': 'err', 'msg': 'You\'re not allowed to do that'}))

        cache.clear()
        return '200'
    else:
        return redirect(url_for('home', message={'category': 'err', 'msg': 'You\'re not allowed to do that'}))


@app.route('/comment/upvote&<id>', methods=['POST'])
def comment_upvote(id):
    """ 
    Allows the user to upvote comments, makes a patch request to the associated comment.
    The comment's vote counter is incremented by 1.
    """

    cid = id[:24]
    sid = id[24:] or None

    if 'auth' in session:
        cm = requests.get(API_URL + 'comments/' + cid).json()
        headers = {
            "If-Match": cm['_etag'],
            "Content-Type": "application/json"
        }
        relevant = {
            'data': cm['data'],
            'post_id': cm['post_id'],
            'children': cm['children']
        }

        parentComment = importer.import_(relevant)
        relevantComment = None

        if sid == None:
            # the upvoted entity is a comment
            relevantComment = parentComment
        else:
            # the upvoted entity is a reply
            relevantComment = find(parentComment, lambda reply: 'reply_id' in reply.data and reply.data['reply_id'] == (cid + sid))

        returnCode = None

        if session['auth'][0] in relevantComment.data['voted']['upvote']:
            relevantComment.data['voted']['upvote'].pop(relevantComment.data['voted']['upvote'].index(session['auth'][0]))
            relevantComment.data['vote'] -= 1
            # the post was upvoted, the upvote is cleared - code: 201

            returnCode = '201'
        elif session['auth'][0] in relevantComment.data['voted']['downvote']:
            relevantComment.data['voted']['downvote'].pop(relevantComment.data['voted']['downvote'].index(session['auth'][0]))
            relevantComment.data['voted']['upvote'].append(session['auth'][0])
            relevantComment.data['vote'] += 2
            # the post was downvoted, the user changed it to upvote - code: 202

            returnCode = '202'
        else:
            relevantComment.data['voted']['upvote'].append(session['auth'][0])
            relevantComment.data['vote'] += 1
            # the post wasn't upvoted by the user - code: 200

            returnCode = '200'

        resp = requests.patch(API_URL + 'comments/' + cid, exporter.export(parentComment), headers=headers)

        if resp.status_code != 200:
            return redirect(url_for('home', message={'category': 'err', 'msg': 'Something went wrong'}))

        return returnCode
    else:
        return redirect(url_for('home', message={'category': 'err', 'msg': 'You\'re not allowed to vote a comment without logging in first'}))


@app.route('/comment/downvote&<id>', methods=['POST'])
def comment_downvote(id):
    """ 
    Allows the user to downvote comments, makes a patch request to the associated comment.
    The comment's vote counter is decremented by one.
    """

    cid = id[:24]
    sid = id[24:] or None

    if 'auth' in session:
        cm = requests.get(API_URL + 'comments/' + cid).json()
        headers = {
            "If-Match": cm['_etag'],
            "Content-Type": "application/json"
        }
        relevant = {
            'data': cm['data'],
            'post_id': cm['post_id'],
            'children': cm['children']
        }

        parentComment = importer.import_(relevant)
        relevantComment = None

        if sid == None:
            # the upvoted entity is a comment
            relevantComment = parentComment
        else:
            # the upvoted entity is a reply
            relevantComment = find(parentComment, lambda reply: 'reply_id' in reply.data and reply.data['reply_id'] == (cid + sid))

        returnCode = None

        if session['auth'][0] in relevantComment.data['voted']['downvote']:
            relevantComment.data['voted']['downvote'].pop(relevantComment.data['voted']['downvote'].index(session['auth'][0]))
            relevantComment.data['vote'] += 1
            # the post was downvoted, the downvote is cleared - code: 201

            returnCode = '201'
        elif session['auth'][0] in relevantComment.data['voted']['upvote']:
            relevantComment.data['voted']['upvote'].pop(relevantComment.data['voted']['upvote'].index(session['auth'][0]))
            relevantComment.data['voted']['downvote'].append(session['auth'][0])
            relevantComment.data['vote'] -= 2
            # the post was upvoted, the user changed it to downvote - code: 202

            returnCode = '202'
        else:
            relevantComment.data['voted']['downvote'].append(session['auth'][0])
            relevantComment.data['vote'] -= 1
            # the post wasn't downvoted by the user - code: 200

            returnCode = '200'

        resp = requests.patch(API_URL + 'comments/' + cid, exporter.export(parentComment), headers=headers)

        if resp.status_code != 200:
            return redirect(url_for('home', message={'category': 'err', 'msg': 'Something went wrong'}))

        return returnCode
    else:
        return redirect(url_for('home', message={'category': 'err', 'msg': 'You\'re not allowed to vote a comment without logging in first'}))


@app.route('/comment/reply&<id>', methods=['GET', 'POST'])
def reply_comment(id):
    """
    Allows the user to reply to a specific comment, which will appear on the website hierarchically.
    To describe the problem hierarchically we need to use some sort of tree.
    """

    cid = id[:24]
    sid = id[24:] or None

    if 'auth' in session:
        cm = requests.get(API_URL + 'comments/' + cid).json()

        if request.method == 'POST':
            relevant = {
                'data': cm['data'],
                'post_id': cm['post_id'],
                'children': cm['children']
            }
            form = request.form

            parentComment = importer.import_(relevant)
            
            if parentComment.children and sid:
                searchedReply = find(parentComment, lambda reply: 'reply_id' in reply.data and reply.data['reply_id'] == (cid + sid))
            else:
                searchedReply = False

            reply = {
                'author': session['auth'][1],
                'text': Markup(form['rcm']).striptags(),
                'date': datetime.today().strftime('%Y.%m.%d - %H:%M'),
                'reply_id': cid + str(uuid.uuid4()),
                'deleted': False,
                'vote': 0,
                'voted': {'upvote': [], 'downvote': []}
            }

            if searchedReply:
                replyNode = AnyNode(data=reply, parent=searchedReply)
            else:
                replyNode = AnyNode(data=reply, parent=parentComment)

            headers = {
                "If-Match": cm['_etag'],
                "Content-Type": "application/json"
            }

            resp = requests.patch(API_URL + 'comments/' + cid, exporter.export(parentComment), headers=headers)

            if resp.status_code != 200:
                return redirect(url_for('home', message={'category': 'err', 'msg': 'Something went wrong'}))

        cache.clear()
        return redirect(url_for('post', id=cm['post_id']))
    else:
        return redirect(url_for('home', message={'category': 'err', 'msg': 'Sign in first to reply to a comment'}))

@app.route('/write', methods=['POST', 'GET'])
def write():
    """
    Write route, a logged in user can write new posts, which are automatically POST-ed to the database collection.
    If a not logged in user tries to request this page, the user is automatically redirected to the home page with a message.
    """

    if 'auth' in session:
        if request.method == 'POST':
            form = request.form
            if form['post'] != '':
                post = {
                    'title': Markup(form['title']).striptags(),
                    'text': form['post'] ,
                    'date': datetime.today().strftime('%Y.%m.%d'),
                    'author': session['auth'][1]
                }

                resp = requests.post(API_URL + 'posts/', post)

                if resp.status_code != 201:
                    return redirect(url_for('home', message={'category': 'err', 'msg': 'Something went wrong'}))

                return redirect(url_for('home', message={'category': 'gr', 'msg': 'Successfully published the post'}))
            else:
                return redirect(url_for('home', message={'category': '', 'msg': 'Your post was empty, it isn\'t published'})) 

        write_template = env.get_template('write.html')
        return write_template.render(title='Write a quick post')
    else:
        return redirect(url_for('home', message={'category': 'err', 'msg': 'You\'re not logged in'}))


@app.route('/edit/<id>', methods=['POST', 'GET'])
def edit(id):
    """ 
    A logged in user can edit his own posts which the user created.
    If the user tries to reach this page unlogged or tries the edit someone else's post, the user is automatically
    redirected to the home page with an appropriate message.
    """

    post_url = API_URL + 'posts/' + id
    post = requests.get(post_url).json()

    if 'auth' in session and session['auth'][1] == post['author']:
        if request.method == 'GET':
            edit_template = env.get_template('edit.html')
            return edit_template.render(title='Edit your post', post=post, id=id)
        elif request.method == 'POST':
            form = request.form
            if form['post'] != '':
                headers = {
                    "If-Match": post['_etag']
                }

                post = {
                    "title": Markup(form['title']).striptags(),
                    "text": form['post']
                }

                resp = requests.patch(post_url, post, headers=headers)

                if resp.status_code != 200:
                    return redirect(url_for('home', message={'category': 'err', 'msg': 'Something went wrong'}))

                return redirect(url_for('home', message={'category': 'gr', 'msg': 'You\'ve successfully edited your posted'}))
            else:
                return redirect(url_for('home', message={'category': '', 'msg': 'Your post was empty, it isn\'t published'}))
    elif 'auth' in session:
        return redirect(url_for('home', message={'category': 'err', 'msg': 'You\'re not the original author of this post'}))
    else:
        return redirect(url_for('home', message={'category': 'err', 'msg': 'You\'re not logged in'}))


@app.route('/delete/<id>', methods=['POST'])
def delete(id):
    """
    A route which only supports POST methods, it is reached when the user clicks on 'delete this post',
    it automatically makes a DELETE request to the database, and simply deletes the associated post.
    If somehow the user tries to reach this route without being logged in, the user is automatically 
    redirected to the home page with an appropriate message.
    """

    if 'auth' in session:
        post_url = API_URL + 'posts/' + id
        post = requests.get(post_url).json()
        headers = {
            "If-Match": post['_etag']
        }

        resp = requests.delete(post_url, headers=headers)

        if resp.status_code != 204:
            return redirect(url_for('home', message={'category': 'err', 'msg': 'Something went wrong'}))

        cache.clear()
        return redirect(url_for('home', message={'category': 'gr', 'msg': 'Your post was successfully deleted'}))
    else:
        return redirect(url_for('home', message={'category': 'err', 'msg': 'You\'re not logged in'}))
    

# * the program starts here
if __name__ == '__main__':
    # ! take out the debug argument
    app.run(port=8000, debug=True)