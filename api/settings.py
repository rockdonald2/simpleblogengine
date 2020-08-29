
# * the mongoDB connection details
MONGO_HOST = 'localhost'
MONGO_PORT = 27017

# * we specify which route refers to the api, and which mongoDB collection we expose with our api
URL_PREFIX = 'api'
MONGO_DBNAME = 'blog'

# * we limit which methods can be used on collections/documents
RESOURCE_METHODS = ['GET', 'POST']
ITEM_METHODS = ['GET', 'PATCH', 'DELETE']

# * Cache-control
CACHE_CONTROL = 'max-age=20'
CACHE_EXPIRES = 20
SORTING = True

# * database-schema
DOMAIN = {
    'posts': {
        'schema': {
            'title': {'type': 'string', 'minlength': 5, 'maxlength': 90, 'required': True},
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

# * The X_DOMAINS setting specify which domains are allowed to make CORS requests
""" X_DOMAINS = '*' """
# * disables HATEOAS and PAGINATION
# * HATEOAS refers to the links, which can be used to navigate through the api without knowing its structure
# * Disabling PAGINATION results in getting all the information in one request
HATEOAS = False
PAGINATION = False