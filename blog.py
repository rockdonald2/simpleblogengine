from flask import Flask, request, url_for, redirect, Response, session
from jinja2 import Environment, FileSystemLoader, select_autoescape, Markup
import requests
import markdown
import pymdownx
import bcrypt
from os import urandom
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = urandom(16)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=2)

API_URL = 'http://127.0.0.1:5000/api/'

env = Environment(
    loader=FileSystemLoader('templates/'),
    autoescape=select_autoescape(['html', 'xml'])
)
extension_configs = {
    "pymdownx.highlight": {
        "guess_lang": True,
        "linenums": True,
        "use_pygments": True,
        "noclasses": True,
        "linenums": False
    }
}
extensions = ['meta', 'attr_list', 'wikilinks', 'pymdownx.extra', 'admonition', 'smarty', 'nl2br', 'sane_lists', 'pymdownx.betterem', 'pymdownx.caret', 'pymdownx.critic', 'pymdownx.emoji', 'pymdownx.highlight', 'pymdownx.magiclink', 'pymdownx.mark', 'pymdownx.saneheaders', 'pymdownx.superfences', 'pymdownx.tilde']
md = markdown.Markdown(extensions=extensions, extension_configs=extension_configs)
env.filters['markdown'] = lambda text: Markup(md.convert(text))
env.trim_blocks = True
env.lstrip_blocks = True

# disable caching, to always see changes in CSS/JS files
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 20

@app.route('/', methods=['GET'])
@app.route('/home', methods=['GET'])
def home():
    posts = requests.get(API_URL + 'posts?projection={"text": 0}').json()['_items']
    home_template = env.get_template('home.html')
    message = eval(request.args.get('message')) if request.args.get('message') else None 
    return home_template.render(title='A Simple Blog Engine', posts=posts, session=session, message=message)

@app.route('/login', methods=['POST', 'GET'])
def login():
    login_template = env.get_template('login.html')

    if 'auth' in session:
        return redirect(url_for('home'))
    elif request.method == 'GET':
        return login_template.render(title='Log into your account')
    elif request.method == 'POST':
        email = request.form['email']
        pwd = request.form['pwd']
        
        existing_user = requests.get(API_URL + 'users?where={"email":"' + email + '"}').json()['_items']
        if existing_user:
            if bcrypt.hashpw(pwd.encode('utf-8'), existing_user[0]['pwd'].encode('utf-8')) == existing_user[0]['pwd'].encode('utf-8'):
                session.permanent = True
                session['auth'] = (email, existing_user[0]['name'])
                return redirect(url_for('home', message={'category': 'gr', 'msg': 'You\'ve successfully logged in!'}))

        return login_template.render(title='Log into your account', message={'category': 'err', 'msg': 'Invalid login credentials'})

@app.route('/logout', methods=['GET'])
def logout():
    session.pop('auth', None)
    return redirect(url_for('home', message={'category': 'gr', 'msg': 'You\'ve successfully logged out!'}))

@app.route('/post/<id>', methods=['GET'])
def post(id):
    post_template = env.get_template('post.html')
    p = requests.get(API_URL + 'posts/' + id).json()
    return post_template.render(title = p['title'], post=p, session=session, id=id)

@app.route('/write', methods=['POST', 'GET'])
def write():
    if 'auth' in session:
        if request.method == 'POST':
            form = request.form
            if form['post'] != '':
                post = {
                    'title': form['title'],
                    'text': form['post'] ,
                    'date': datetime.today().strftime('%Y.%m.%d'),
                    'author': session['auth'][1]
                }

                requests.post(API_URL + 'posts/', post)

                return redirect(url_for('home', message={'category': 'gr', 'msg': 'Successfully published the post'}))
            else:
                return redirect(url_for('home', message={'category': '', 'msg': 'Your post was empty, it isn\'t published'}))
            
        
        write_template = env.get_template('write.html')
        return write_template.render(title='Write a quick post')
    else:
        return redirect(url_for('home', message={'category': 'err', 'msg': 'You\'re not logged in'}))

@app.route('/edit/<id>', methods=['POST', 'GET'])
def edit(id):
    if 'auth' in session:
        post_url = API_URL + 'posts/' + id

        post = requests.get(post_url).json()

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
                    "text": form['post']
                }

                requests.patch(post_url, post, headers=headers)
                return redirect(url_for('home', message={'category': 'gr', 'msg': 'You\'ve successfully edited your posted'}))
            else:
                return redirect(url_for('home', message={'category': '', 'msg': 'Your post was empty, it isn\'t published'}))
    else:
        return redirect(url_for('home', message={'category': 'err', 'msg': 'You\'re not logged in'}))

@app.route('/delete/<id>', methods=['POST'])
def delete(id):
    if 'auth' in session:
        post_url = API_URL + 'posts/' + id
        post = requests.get(post_url).json()
        headers = {
            "If-Match": post['_etag']
        }
        requests.delete(post_url, headers=headers)

        return redirect(url_for('home', message={'category': 'gr', 'msg': 'Your post was successfully deleted'}))
    else:
        return redirect(url_for('home', message={'category': 'err', 'msg': 'You\'re not logged in'}))

if __name__ == '__main__':
    app.run(port=8000, debug=True)