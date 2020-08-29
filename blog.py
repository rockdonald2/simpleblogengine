from flask import Flask, request, url_for, redirect, session
from flask_caching import Cache
from jinja2 import Environment, FileSystemLoader, select_autoescape, Markup
import requests
import markdown
import pymdownx
from bcrypt import hashpw
from os import urandom
from datetime import datetime, timedelta

# * Starting flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = urandom(16)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=2)
# * cache-control
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 20
app.config['CACHE_TYPE'] = 'simple'
app.config['CACHE_DEFAULT_TIMEOUT'] = 300
cache = Cache(app)

# * The API can be reached with this endpoint
API_URL = 'http://127.0.0.1:5000/api/'

# * Environment used in JINJA2 templates
env = Environment(
    loader=FileSystemLoader('templates/'),
    autoescape=select_autoescape(['html', 'xml'])
)

# * Extensions for the markdow JINJA2 filter
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

# * Cache current posts for 2 minutes
# * This also results in new posts not appearing for 2 minutes after publishing
@cache.cached(timeout=120, key_prefix='all_posts')
def get_all_posts():
    posts = requests.get(API_URL + 'posts?projection={"text": 0}').json()['_items']
    return posts

@app.route('/', methods=['GET'])
@app.route('/home', methods=['GET'])
def home():
    """
    Index route, where the page loads,
    can take in a message in the form of a query string.
    The posts are cached for 2 minutes after loading.
    """

    cached_posts = get_all_posts()
    home_template = env.get_template('home.html')
    message = eval(request.args.get('message')) if request.args.get('message') else None 
    return home_template.render(title='A Simple Blog Engine', posts=cached_posts, session=session, message=message)
    

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
                session['auth'] = (email, existing_user[0]['name'])
                return redirect(url_for('home', message={'category': 'gr', 'msg': 'You\'ve successfully logged in!'}))

        return login_template.render(title='Log into your account', message={'category': 'err', 'msg': 'Invalid login credentials'})


@app.route('/logout', methods=['GET'])
def logout():
    """
    Logout logic, manually clears the session associated to the user,
    after logging out redirects the user to the home page with a message
    """

    session.pop('auth', None)
    return redirect(url_for('home', message={'category': 'gr', 'msg': 'You\'ve successfully logged out!'}))


@app.route('/post/<id>', methods=['GET'])
def post(id):
    """ 
    This route displays one post, requested from the database with an ID associated to the post.
    Each id is unique.
    """

    post_template = env.get_template('post.html')
    p = requests.get(API_URL + 'posts/' + id).json()
    return post_template.render(title=p['title'], post=p, session=session, id=id)


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
                    'title': Markup.escape(form['title']),
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
                    "title": Markup.escape(form['title']),
                    "text": form['post']
                }

                resp = requests.patch(post_url, post, headers=headers)

                if resp.status_code != 200:
                    return redirect(url_for('home', messagae={'category': 'err', 'msg': 'Something went wrong'}))

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

        return redirect(url_for('home', message={'category': 'gr', 'msg': 'Your post was successfully deleted'}))
    else:
        return redirect(url_for('home', message={'category': 'err', 'msg': 'You\'re not logged in'}))

# * the program starts here
if __name__ == '__main__':
    app.run(port=8000, debug=True)