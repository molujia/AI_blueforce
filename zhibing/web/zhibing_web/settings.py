from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
SECRET_KEY = "zhibing-dev-only"
DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
ROOT_URLCONF = "zhibing_web.urls"
INSTALLED_APPS = ["django.contrib.staticfiles", "command_ui"]
MIDDLEWARE = []
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "command_ui" / "static"]
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "command_ui" / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": []},
}]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"