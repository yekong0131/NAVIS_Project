from django.apps import AppConfig
import sys
import os


def dev_print(*args, **kwargs):
    if os.getenv("APP_ENV") == "development":
        print(*args, **kwargs)


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
