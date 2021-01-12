from blogengine import app, cache, API_URL
from blogengine.forms import LoginForm, RegistrationForm, CommentForm, ReplyForm, PostForm
from blogengine.utility import human_format, check_login, get_all_posts, childs_are_deleted

from flask import request, url_for, redirect, session, abort, jsonify, render_template, flash
from werkzeug.datastructures import MultiDict
from jinja2 import Markup
import requests
from bcrypt import hashpw, gensalt
from datetime import datetime
from json import dumps
import uuid
from anytree import AnyNode, find
from anytree.exporter import JsonExporter
from anytree.importer import DictImporter


# * tree exporter to JSON
exporter = JsonExporter()
# * tree importer to Dict
importer = DictImporter()

# ! Oldd meg a kommentfa problémát, a jelenlegi ötlet, ami eszembejutott, hogy minden törléskor a kommentfa tetejéről indulva ellenőrízze le az összes elágazást, így az utolsó törlésekor az összeset töröltnek
# ! fogja nézni, megoldva azt a problémát, hogy minden kommentet időközönként megkelljen nézni.
# ! nézd meg a jegyzetfűzetet is a potenciális megoldással

@app.errorhandler(404)
@app.errorhandler(405)
@app.errorhandler(500)
@app.errorhandler(403)
def error_handler(e):
    return render_template('error.html', title=str(e))


@app.route('/posts', methods=['GET'])
def posts():
    """
    An endpoint to fetch current posts for homepage type-ahead effect.
    """

    # * We need to filter out additional fields added to each response: _updated, _created, _etag.
    # ! We do not want to expose these fields to end users.

    all_posts = get_all_posts()
    restricted = ['_updated', '_created', '_etag']

    for p in all_posts[:]:
        for field in list(p):
            if field in restricted:
                del(p[field])

    return jsonify(all_posts)


@app.route('/', methods=['GET'])
@app.route('/home', methods=['GET'])
def home():
    """
    Index route, where the page loads,
    can take in a message in the form of a query string.
    The posts are cached for 2 minutes after loading, for users that aren't logged in.
    """

    return render_template('home.html', title='A Simple Blog Engine', session=session)


@app.route('/login', methods=['POST', 'GET'])
def login():
    """
    Login form where one user can log in,
    users are loaded from the mongoDB collection by a GET request.
    The logged in user is saved in session for 2 days.
    If a user refers to this page, after logging in, it automatically redirects the user to the home page,
    with a message
    """

    form = LoginForm()

    if check_login():
        flash('You\'re already logged in!')
        return redirect(url_for('home'))

    if form.validate_on_submit():
        existing_user = requests.get(API_URL + 'users?where={"email":"' + form.email.data + '"}').json()['_items']
        if existing_user:
            if hashpw(form.password.data.encode('utf-8'), existing_user[0]['pwd'].encode('utf-8')) == existing_user[0]['pwd'].encode('utf-8'):
                session.permanent = True
                session['auth'] = (form.email.data, existing_user[0]['name'], existing_user[0]['writer'], existing_user[0]['_id'][14:])

                flash('You\'ve successfully logged in!', category='succ')
                return redirect(url_for('home'))

        flash('Invalid credentials', category='err')
        return render_template('login.html', title='Log into your account', form=form)

    return render_template('login.html', title='Log into your account', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Registers a new user, makes a POST request to the users collection.
    """

    form = RegistrationForm()

    if check_login():
        flash('Sign out first before registering a new account', category='succ')
        return redirect(url_for('home'))

    if form.validate_on_submit():
        user = {
            'email': form.email.data,
            'name': Markup(form.name.data).striptags(),
            'pwd': hashpw(form.password.data.encode('utf-8'), gensalt()),
            'writer': False
        }

        resp = requests.post(API_URL + 'users/', user)

        if resp.status_code != 201:
            flash('Something went wrong', category='err')
            return redirect(url_for('home'))

        flash('You\'ve successfully created your account, now you can log in!', category='succ')
        return redirect(url_for('home'))

    return render_template('register.html', title='Register your new account', form=form)


@app.route('/logout', methods=['GET'])
def logout():
    """
    Logout logic, manually clears the session associated to the user,
    after logging out redirects the user to the home page with a message
    """

    session.pop('auth', None)
    flash('You\'ve successfully logged out!', category='succ')
    return redirect(url_for('home'))


@app.route('/post/<id>', methods=['GET'])
@cache.cached(timeout=120, unless=check_login)
def post(id):
    """ 
    This route displays one post, requested from the database with an ID associated to the post.
    Each id is unique.
    """

    # * We need this to "remember" previous errors
    if 'formdataC' in session:
        cForm = CommentForm(MultiDict(session['formdataC']))
        cForm.validate()
    else:
        cForm = CommentForm()

    if 'formdataR' in session:
        rForm = ReplyForm(MultiDict(session['formdataR']))
        rForm.validate()
    else:
        rForm = ReplyForm()

    session.pop('formdataC', None) if 'formdataC' in session else ''
    session.pop('formdataR', None) if 'formdataR' in session else ''

    p = requests.get(API_URL + 'posts/' + id)

    if p.status_code == 404:
        abort(404, "Post not found")
    else:
        p = p.json()

    comments = requests.get(API_URL + 'comments?where={"post_id":"' + id + '"}').json()['_items']
    comments.sort(reverse=True, key=lambda c: c['data']['vote'])

    return render_template('post.html', title=p['title'], post=p, session=session, id=id, comments=comments, human_format=human_format, cForm=cForm, rForm=rForm)


@app.route('/comment&<id>', methods=['POST'])
def comment(id):
    """
    Allows the user to post comments, automatically makes a post request to the database.
    After the post refreshes the post uncached with new comments.
    """

    form = CommentForm()

    if check_login():
        if form.validate_on_submit():
            headers = {
                'Content-Type': 'application/json'
            }

            comment = {
                'author': session['auth'][1],
                'author_id': session['auth'][3],
                'text': Markup(form.comment.data).striptags(),
                'date': datetime.today().strftime('%Y.%m.%d - %H:%M')
            }

            resp = requests.post(API_URL + 'comments/', exporter.export(AnyNode(data=comment, post_id=id)), headers=headers)

            if resp.status_code != 201:
                flash('Something went wrong')
                return redirect(url_for('home'))

            cache.clear()
        elif form.is_submitted() and not form.validate():
            session['formdataC'] = request.form

        return redirect(url_for('post', id=id))
    else:
        flash('You\'re not logged in to comment on this post', category='err')
        return redirect(url_for('home'))


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

    if check_login():
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
            if (session['auth'][1] == cm['data']['author'] and session['auth'][3] == cm['data']['author_id']) or session['auth'][1] == postAuthor:
                # * Has no child replies
                if not cm['children']:
                    resp = requests.delete(API_URL + 'comments/' + cid, headers=headers)

                    if resp.status_code != 204:
                        flash('Something went wrong', category='err')
                        return redirect(url_for('home'))
                # * Has child replies
                else:
                    # * Check whether all of its child replies are deleted or not
                    resp = None

                    parentComment = importer.import_(relevant)

                    # * If they are, then delete the whole tree
                    if childs_are_deleted(parentComment):
                        resp = requests.delete(API_URL + 'comments/' + cid, headers=headers)

                        if resp.status_code != 204:
                            flash('Something went wrong', category='err')
                            return redirect(url_for('home'))
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
                        flash('Something went wrong', category='err')
                        return redirect(url_for('home'))
            else:
                flash('You\'re not allowed to do that', category='err')
                return redirect(url_for('home'))
        else:
            # * Post is a reply

            parentComment = importer.import_(relevant)
            searchedReply = find(parentComment, lambda reply: 'reply_id' in reply.data and reply.data['reply_id'] == id)

            if (session['auth'][1] == searchedReply.data['author'] and session['auth'][3] == searchedReply.data['author_id']) or session['auth'][1] == postAuthor:
                resp = None
                searchedParent = searchedReply.parent

                if searchedReply.children and not childs_are_deleted(searchedReply):
                    searchedReply.data['text'] = 'This comment was deleted'
                    searchedReply.data['deleted'] = True
                    resp = requests.patch(API_URL + 'comments/' + cid, exporter.export(parentComment), headers=headers)
                else:
                    searchedParent.children = tuple(filter(lambda reply: reply.data['reply_id'] != id, searchedParent.children))

                    # * Check for deleted parent, if parent is deleted, then delete the whole tree
                    if searchedParent.data['deleted']:
                        while searchedParent and searchedParent.data['deleted']:
                            if childs_are_deleted(searchedParent):
                                # * If a parents' children are all deleted, delete the whole tree
                                # * We need to check if that parent is a comment or a reply
                                # * If it has a reply_id field, then it is a reply
                                if 'reply_id' in searchedParent.data:
                                    # * If it is a reply, we need to filter that deleted branch
                                    searchedParent.parent.children = tuple(filter(lambda reply: reply.data['reply_id'] != searchedParent.data['reply_id'], searchedParent.parent.children)) or ()
                                else:
                                    # * If not, it is a comment, and we delete it
                                    resp = requests.delete(API_URL + 'comments/' + cid, headers=headers)
                                    break

                                searchedParent = searchedParent.parent
                            else:
                                break

                        # * If whole tree became empty, because of clearing
                        if not searchedParent:
                            resp = requests.delete(API_URL + 'comments/' + cid, headers=headers)

                        if not resp:
                            # * If we didn't end up at the top of tree, and the comment root isn't deleted we update the root
                            # * Else, the comment root is already deleted
                            resp = requests.put(API_URL + 'comments/' + cid, exporter.export(parentComment), headers=headers)
                    else:
                        resp = requests.put(API_URL + 'comments/' + cid, exporter.export(parentComment), headers=headers)

                if resp.status_code != 200 and resp.status_code != 204:
                    flash('Something went wrong', category='err')
                    return redirect(url_for('home'))
            else:
                flash('You\'re not allowed to do that', category='err')
                return redirect(url_for('home'))

        cache.clear()
        return '200'
    else:
        flash('You\'re not allowed to do that', category='err')
        return redirect(url_for('home'))


@app.route('/comment/upvote&<id>', methods=['POST'])
def comment_upvote(id):
    """ 
    Allows the user to upvote comments, makes a patch request to the associated comment.
    The comment's vote counter is incremented by 1.
    """

    cid = id[:24]
    sid = id[24:] or None

    if check_login():
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

        if session['auth'][3] in relevantComment.data['voted']['upvote']:
            relevantComment.data['voted']['upvote'].pop(relevantComment.data['voted']['upvote'].index(session['auth'][3]))
            relevantComment.data['vote'] -= 1
            # the post was upvoted, the upvote is cleared - code: 201

            returnCode = '201'
        elif session['auth'][3] in relevantComment.data['voted']['downvote']:
            relevantComment.data['voted']['downvote'].pop(relevantComment.data['voted']['downvote'].index(session['auth'][3]))
            relevantComment.data['voted']['upvote'].append(session['auth'][3])
            relevantComment.data['vote'] += 2
            # the post was downvoted, the user changed it to upvote - code: 202

            returnCode = '202'
        else:
            relevantComment.data['voted']['upvote'].append(session['auth'][3])
            relevantComment.data['vote'] += 1
            # the post wasn't upvoted by the user - code: 200

            returnCode = '200'

        # * if the upvoted entity is a reply, then sort that level
        if not relevantComment.is_root:
            relevantParent = relevantComment.parent
            relevantChildren = list(relevantParent.children)
            relevantChildren.sort(reverse=True, key=lambda c: c.data['vote'])
            relevantParent.children = tuple(relevantChildren)

        resp = requests.patch(API_URL + 'comments/' + cid, exporter.export(parentComment), headers=headers)

        if resp.status_code != 200:
            flash('Something went wrong', category='err')
            return redirect(url_for('home'))

        return returnCode
    else:
        flash('You\'re not allowed to vote on a comment without logging in first', category='err')
        return redirect(url_for('home'))


@app.route('/comment/downvote&<id>', methods=['POST'])
def comment_downvote(id):
    """ 
    Allows the user to downvote comments, makes a patch request to the associated comment.
    The comment's vote counter is decremented by one.
    """

    cid = id[:24]
    sid = id[24:] or None

    if check_login():
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

        if session['auth'][3] in relevantComment.data['voted']['downvote']:
            relevantComment.data['voted']['downvote'].pop(relevantComment.data['voted']['downvote'].index(session['auth'][3]))
            relevantComment.data['vote'] += 1
            # the post was downvoted, the downvote is cleared - code: 201

            returnCode = '201'
        elif session['auth'][3] in relevantComment.data['voted']['upvote']:
            relevantComment.data['voted']['upvote'].pop(relevantComment.data['voted']['upvote'].index(session['auth'][3]))
            relevantComment.data['voted']['downvote'].append(session['auth'][3])
            relevantComment.data['vote'] -= 2
            # the post was upvoted, the user changed it to downvote - code: 202

            returnCode = '202'
        else:
            relevantComment.data['voted']['downvote'].append(session['auth'][3])
            relevantComment.data['vote'] -= 1
            # the post wasn't downvoted by the user - code: 200

            returnCode = '200'

        # * if the upvoted entity is a reply, then sort that level
        if not relevantComment.is_root:
            relevantParent = relevantComment.parent
            relevantChildren = list(relevantParent.children)
            relevantChildren.sort(reverse=True, key=lambda c: c.data['vote'])
            relevantParent.children = tuple(relevantChildren)

        resp = requests.patch(API_URL + 'comments/' + cid, exporter.export(parentComment), headers=headers)

        if resp.status_code != 200:
            flash('Something went wrong', category='err')
            return redirect(url_for('home'))

        return returnCode
    else:
        flash('You\'re not allowed to vote on a comment without logging in first', category='err')
        return redirect(url_for('home'))


@app.route('/comment/reply&<id>', methods=['POST'])
def reply_comment(id):
    """
    Allows the user to reply to a specific comment, which will appear on the website hierarchically.
    To describe the problem hierarchically we need to use some sort of tree.
    """

    cid = id[:24]
    sid = id[24:] or None

    form = ReplyForm()

    if check_login():
        cm = requests.get(API_URL + 'comments/' + cid).json()

        if form.validate_on_submit():
            relevant = {
                'data': cm['data'],
                'post_id': cm['post_id'],
                'children': cm['children']
            }

            parentComment = importer.import_(relevant)

            if parentComment.children and sid:
                searchedReply = find(parentComment, lambda reply: 'reply_id' in reply.data and reply.data['reply_id'] == (cid + sid))
            else:
                searchedReply = False

            reply = {
                'author': session['auth'][1],
                'author_id': session['auth'][3],
                'text': Markup(form.reply.data).striptags(),
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
                flash('Something went wrong', category='err')
                return redirect(url_for('home'))

            cache.clear()
        elif form.is_submitted() and not form.validate():
            session['formdataR'] = request.form

        return redirect(url_for('post', id=cm['post_id']))
    else:
        flash('Sign in first to reply to a comment', category='err')
        return redirect(url_for('home'))


@app.route('/write', methods=['GET', 'POST'])
def write():
    """
    Write route, a logged in user can write new posts, which are automatically POST-ed to the database collection.
    If a not logged in user tries to request this page, the user is automatically redirected to the home page with a message.
    """

    form = PostForm()

    if check_login():
        if form.validate_on_submit():
            post = {
                'title': Markup(form.title.data).striptags(),
                'text': form.post.data,
                'date': datetime.today().strftime('%Y.%m.%d'),
                'author': session['auth'][1],
                'author_id': session['auth'][3]
            }

            resp = requests.post(API_URL + 'posts/', post)

            if resp.status_code != 201:
                flash('Something went wrong', category='err')
                return redirect(url_for('home'))

            flash('You\'ve successfully published the post', category='succ')
            return redirect(url_for('home'))

        return render_template('write.html', title='Write your post', form=form)
    else:
        flash('You\'re not logged in to write a post')
        return redirect(url_for('home'))


@app.route('/edit/<id>', methods=['GET', 'POST'])
def edit(id):
    """ 
    A logged in user can edit his own posts which the user created.
    If the user tries to reach this page unlogged or tries the edit someone else's post, the user is automatically
    redirected to the home page with an appropriate message.
    """

    post_url = API_URL + 'posts/' + id
    post = requests.get(post_url).json()

    form = PostForm()

    if check_login() and session['auth'][1] == post['author']:
        if form.validate_on_submit():
            headers = {
                "If-Match": post['_etag']
            }

            post = {
                "title": Markup(form.title.data).striptags(),
                "text": form.post.data
            }

            resp = requests.patch(post_url, post, headers=headers)

            if resp.status_code != 200:
                flash('Something went wrong', category='err')
                return redirect(url_for('home'))

            flash('You\'ve successfully editer your post', category='succ')
            return redirect(url_for('home'))

        return render_template('edit.html', title='Edit your post', post=post, id=id, form=form)
    elif check_login():
        flash('You\'re not the original author of this post', category='err')
        return redirect(url_for('home'))
    else:
        flash('You\'re not logged in', category='err')
        return redirect(url_for('home'))


@app.route('/delete/<id>', methods=['POST'])
def delete(id):
    """
    A route which only supports POST methods, it is reached when the user clicks on 'delete this post',
    it automatically makes a DELETE request to the database, and simply deletes the associated post.
    If somehow the user tries to reach this route without being logged in, the user is automatically 
    redirected to the home page with an appropriate message.
    After deleting the post, it makes a search for every comment associated to this post and deletes them.
    """

    if check_login():
        post_url = API_URL + 'posts/' + id
        post = requests.get(post_url).json()
        headers = {
            "If-Match": post['_etag']
        }

        resp = requests.delete(post_url, headers=headers)

        if resp.status_code != 204:
            flash('Something went wrong', category='err')
            return redirect(url_for('home'))

        comments = requests.get(API_URL + 'comments?where={"post_id":"' + id + '"}').json()['_items']
        COMMENTS_URL = API_URL + 'comments/'

        for c in comments:
            comment_headers = {
                "If-Match": c['_etag']
            }

            resp = requests.delete(COMMENTS_URL + c['_id'], headers=comment_headers)

            if resp.status_code != 204:
                flash('Something went wrong', category='err')
                return redirect(url_for('home'))

        cache.clear()

        flash('Your post was successfully deleted', category='succ')
        return redirect(url_for('home'))
    else:
        flash('You\'re not logged in', category='err')
        return redirect(url_for('home'))