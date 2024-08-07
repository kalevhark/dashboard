"""
Django settings for dashboard project.

Generated by 'django-admin startproject' using Django 3.1.2.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.1/ref/settings/
"""

from pathlib import Path, PurePath

# Tundliku info eraldamiseks programmifailidest
# Kasutus KEY = config('KEY')
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# SECRET_KEY = '2t9t)72s)g=l761t^egn0w&q93z+a(0h8eh)$ez0h+7xa*e4jb'
SECRET_KEY = config('SECRET_KEY')

DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = [
    's9a', 's9a.lan', '192.168.1.158',
    'localhost', '127.0.0.1'
]

# Application definition

INSTALLED_APPS = [
    'channels',
    'app',
    'chat',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'dashboard.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'dashboard.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': PurePath.joinpath(BASE_DIR, 'db.sqlite3'),
        'TEST': {
            'NAME': PurePath.joinpath(BASE_DIR, 'db_test.sqlite3')
        }
    }
}


# Password validation
# https://docs.djangoproject.com/en/3.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.1/topics/i18n/

LANGUAGE_CODE = 'et'

TIME_ZONE = 'Europe/Tallinn'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/

STATIC_ROOT = PurePath.joinpath(BASE_DIR, 'static/')
STATIC_URL = '/static/'

# Channels
ASGI_APPLICATION = 'dashboard.routing.application'
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}

# app
AQUAREA_USR = config('AQUAREA_USR')
AQUAREA_PWD = config('AQUAREA_PWD')
AQUAREA_PWD_SERVICE = config('AQUAREA_PWD_SERVICE')
AQUAREA_ACCESS_TOKEN = config('AQUAREA_accessToken')
AQUAREA_SELECTEDGWID = config('AQUAREA_selectedGwid')
AQUAREA_SELECTEDDEVICEID = config('AQUAREA_selectedDeviceId')

TUYA_USER=config('TUYA_USER')
TUYA_USER_PASSWORD=config('TUYA_USER_PASSWORD')
TUYA_DEVICE_ID = config('TUYA_DEVICE_ID')
TUYA_IP_ADDRESS = config('TUYA_IP_ADDRESS')
TUYA_LOCAL_KEY = config('TUYA_LOCAL_KEY')
TUYA_DEVICE_ID_2 = config('TUYA_DEVICE_ID_2')
TUYA_IP_ADDRESS_2 = config('TUYA_IP_ADDRESS_2')
TUYA_LOCAL_KEY_2 = config('TUYA_LOCAL_KEY_2')

EZR_IP_ADDRESS = config('EZR_IP_ADDRESS')