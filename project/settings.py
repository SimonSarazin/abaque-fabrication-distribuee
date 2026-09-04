import os
import json
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DEBUG = os.environ.get("DEBUG", "true").lower() in ("true", "1", "yes")

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key" if DEBUG else "")
if not SECRET_KEY:
    raise ImproperlyConfigured("SECRET_KEY environment variable is required when DEBUG is false")

if "ALLOWED_HOSTS" in os.environ:
    ALLOWED_HOSTS = [h.strip() for h in os.environ["ALLOWED_HOSTS"].split(",") if h.strip()]
elif DEBUG:
    ALLOWED_HOSTS = ["*"]
else:
    ALLOWED_HOSTS = []

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"

AUTHENTICATION_BACKENDS = [
    "abaque.oidc_backend.AbaqueOIDCBackend",
    "django.contrib.auth.backends.ModelBackend",
]

OIDC_RP_CLIENT_ID = os.environ.get("OIDC_CLIENT_ID", "")
OIDC_RP_CLIENT_SECRET = os.environ.get("OIDC_CLIENT_SECRET", "")

OIDC_DISCOVERY_URL = os.environ.get("OIDC_DISCOVERY_URL", "")
OIDC_DISCOVERY = {}
if OIDC_DISCOVERY_URL:
    try:
        with urlopen(OIDC_DISCOVERY_URL, timeout=10) as response:
            OIDC_DISCOVERY = json.load(response)
    except (OSError, URLError, ValueError) as error:
        raise ImproperlyConfigured("Unable to load OIDC discovery document") from error

OIDC_OP_AUTHORIZATION_ENDPOINT = OIDC_DISCOVERY.get("authorization_endpoint", "")
OIDC_OP_TOKEN_ENDPOINT = OIDC_DISCOVERY.get("token_endpoint", "")
OIDC_OP_USER_ENDPOINT = OIDC_DISCOVERY.get("userinfo_endpoint", "")
OIDC_OP_JWKS_ENDPOINT = OIDC_DISCOVERY.get("jwks_uri", "")
OIDC_RP_IDP_SIGN_KEY = os.environ.get("OIDC_IDP_SIGN_KEY") or None
OIDC_RP_SIGN_ALGO = os.environ.get("OIDC_SIGN_ALGORITHM", "RS256")
OIDC_RP_SCOPES = "openid email profile"

LANGUAGE_CODE = "fr"

TIME_ZONE = "Europe/Paris"
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "mozilla_django_oidc",
    "abaque",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    # nginx terminates TLS and proxies over plain HTTP; without this header
    # trust, SECURE_SSL_REDIRECT would loop forever (see DEPLOY.md).
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

ROOT_URLCONF = "project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": [
            "django.template.context_processors.debug",
            "django.template.context_processors.request",
            "django.contrib.auth.context_processors.auth",
            "django.contrib.messages.context_processors.messages",
        ]},
    }
]

WSGI_APPLICATION = "project.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# WhiteNoise serves the collected static files with hashed names and
# far-future caching; in DEBUG the unhashed names are used automatically.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
