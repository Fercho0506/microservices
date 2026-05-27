import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRET_KEY = os.environ.get('SECRET_KEY', 'finops-dev-secret-key-change-in-prod')
DEBUG = os.environ.get('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'expenses',
    'corsheaders',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'expenses.middleware.JWTAuthMiddleware',
]

ROOT_URLCONF = 'finops.urls'
WSGI_APPLICATION = 'finops.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'finops_db'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'postgres'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

# Auth0 Config
AUTH0_DOMAIN = os.environ.get('AUTH0_DOMAIN', 'your-tenant.auth0.com')
AUTH0_AUDIENCE = os.environ.get('AUTH0_AUDIENCE', 'https://bite-finops-api')
REQUIRED_ROLES = ['finops', 'admin']

# Cache (Redis via ElastiCache)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': f"redis://{os.environ.get('REDIS_HOST', 'localhost')}:{os.environ.get('REDIS_PORT', '6379')}",
        'TIMEOUT': 300,
    }
}

# Performance: Cache timeout for expenses query (seconds)
EXPENSES_CACHE_TIMEOUT = int(os.environ.get('EXPENSES_CACHE_TIMEOUT', '300'))

CORS_ALLOW_ALL_ORIGINS = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'loggers': {
        'audit': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}
