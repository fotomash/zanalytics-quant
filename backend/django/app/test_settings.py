import sys, types
pandas_stub = types.ModuleType('pandas')
setattr(pandas_stub, 'DataFrame', object)
sys.modules.setdefault('pandas', pandas_stub)
import os
os.environ.setdefault("DJANGO_SECRET_KEY", "test-secret")
from .settings import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

CELERY_BROKER_URL = 'memory://'
CELERY_RESULT_BACKEND = 'cache+memory://'
LOGGING = {"version": 1, "disable_existing_loggers": True}
