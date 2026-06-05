"""
Django settings — TCC EducaSP Analytics.

Em desenvolvimento, defaults seguros funcionam direto (DEBUG=True, SQLite).
Em produção, exporte ou coloque num .env: SECRET_KEY, DEBUG=False, ALLOWED_HOSTS.
Veja deploy/README.md.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Carrega .env automaticamente se existir (não requer python-dotenv em dev) ──
_env_file = BASE_DIR / '.env'
if _env_file.exists():
    for line in _env_file.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _env_bool(name, default=False):
    return os.environ.get(name, str(default)).lower() in ('1', 'true', 'yes', 'on')


def _env_list(name, default=''):
    raw = os.environ.get(name, default)
    return [x.strip() for x in raw.replace(',', ' ').split() if x.strip()]


# ─── Segurança ────────────────────────────────────────────────────────────────
SECRET_KEY    = os.environ.get('SECRET_KEY', 'dev-insecure-change-me-in-production')
DEBUG         = _env_bool('DEBUG', default=True)
ALLOWED_HOSTS = _env_list('ALLOWED_HOSTS', default='localhost 127.0.0.1')

# Domínios autorizados a enviar POSTs com CSRF (precisa do https:// na frente em prod)
CSRF_TRUSTED_ORIGINS = _env_list('CSRF_TRUSTED_ORIGINS', default='')

# Cabeçalhos de segurança em produção
if not DEBUG:
    SECURE_PROXY_SSL_HEADER       = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT           = _env_bool('SECURE_SSL_REDIRECT', default=True)
    SESSION_COOKIE_SECURE         = True
    CSRF_COOKIE_SECURE            = True
    SECURE_HSTS_SECONDS           = int(os.environ.get('SECURE_HSTS_SECONDS', 0))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0
    SECURE_HSTS_PRELOAD           = SECURE_HSTS_SECONDS > 0
    SECURE_CONTENT_TYPE_NOSNIFF   = True
    SECURE_REFERRER_POLICY        = 'same-origin'
    X_FRAME_OPTIONS               = 'DENY'


# ─── Apps & Middleware ────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'education',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'tcc_webapp.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'tcc_webapp.wsgi.application'


# ─── Banco de dados ───────────────────────────────────────────────────────────
# SQLite por padrão (suficiente para 645 municípios). Para Postgres, defina
# DATABASE_URL=postgres://user:pass@host:5432/dbname e instale dj-database-url.
_database_url = os.environ.get('DATABASE_URL', '')
if _database_url:
    try:
        import dj_database_url
        DATABASES = {'default': dj_database_url.config(default=_database_url, conn_max_age=600)}
    except ImportError:
        raise RuntimeError('DATABASE_URL definido mas dj-database-url não instalado. Rode: pip install dj-database-url psycopg2-binary')
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME':   BASE_DIR / 'db.sqlite3',
        }
    }


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'pt-br'
TIME_ZONE     = 'America/Sao_Paulo'
USE_I18N      = True
USE_TZ        = True


# ─── Static files ─────────────────────────────────────────────────────────────
STATIC_URL  = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Por padrão, graficos/ está em ../graficos relativo ao webapp/
# Em produção pode ser sobrescrito via env GRAFICOS_DIR=/var/www/educasp/graficos
_graficos_dir = Path(os.environ.get('GRAFICOS_DIR', BASE_DIR.parent / 'graficos'))

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
if _graficos_dir.exists():
    STATICFILES_DIRS.append(('graficos', _graficos_dir))

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# ─── Logging básico em produção ───────────────────────────────────────────────
if not DEBUG:
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {'console': {'class': 'logging.StreamHandler'}},
        'root': {'handlers': ['console'], 'level': 'INFO'},
        'loggers': {
            'django': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
            'django.request': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
        },
    }


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
