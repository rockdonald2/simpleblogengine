MONGO_HOST = 'localhost'
MONGO_PORT = 27017

URL_PREFIX = 'api'
MONGO_DBNAME = 'blog'

RESOURCE_METHODS = ['GET', 'POST']
ITEM_METHODS = ['GET', 'PATCH', 'DELETE']

CACHE_CONTROL = 'max-age=20'
CACHE_EXPIRES = 20
SORTING = True

DOMAIN = {
    'posts': {
        'schema': {
            'title': {'type': 'string', 'minlength': 5, 'maxlength': 50, 'required': True},
            'text': {'type': 'string', 'minlength': 15, 'required': True},
            'date': {'type': 'string', 'required': True},
            'author': {'type': 'string', 'required': True}
        }
    },
    'users': {
        'schema': {
            'email': {'type': 'string'},
            'name': {'type': 'string'},
            'pwd': {'type': 'string'}
        }
    }
}

""" X_DOMAINS = '*' """
HATEOAS = False

PAGINATION = False