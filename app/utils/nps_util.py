from datetime import datetime, timedelta
import json
import os
from statistics import mean
import sys

import urllib3
# Vaigistame ssl veateated
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import requests

try:
    from django.conf import settings
    from django.http import JsonResponse
    from app.models import Log
except:
    import os
    import django
    # from django.test.utils import setup_test_environment
    os.environ['DJANGO_SETTINGS_MODULE'] = 'dashboard.settings'
    django.setup()
    # import dev_conf

DEBUG = False
DEGREE_CELSIUS = u'\N{DEGREE CELSIUS}'

m2rgiga = lambda i: ("+" if i > 0 else "") + str(i)

from pytz import timezone
import pytz

MARGINAAL = 0.44 # senti/kWh km-ga
# Kuup2evad
TALLINN = timezone('Europe/Tallinn')
UTC = pytz.utc

# Programmikataloog, mida kasutame ka varundamiseks
path = os.path.dirname(sys.argv[0])

def get_nps_prices(loc_start, loc_end):
    utc_start = loc_start.astimezone(UTC)
    utc_end = loc_end.astimezone(UTC)
    fmt = "%Y-%m-%dT%H:%M:%SZ"

    DATA_URL = 'https://dashboard.elering.ee/api/nps/price'
    params = {
        'start': utc_start.strftime(fmt),
        'end': utc_end.strftime(fmt),
    }

    headers = {}

    csvfile_raw = requests.get(
        DATA_URL,
        params=params,
        headers=headers
    )

    content = csvfile_raw.text
    data = json.loads(content)
    nps_prices = data['data']['ee']
    return nps_prices

def get_nps_12plus12_hour_prices():
    now = datetime.now()
    loc_start = now.astimezone(TALLINN) - timedelta(hours=12)
    loc_end = loc_start + timedelta(days=1)
    nps_12plus12_hour_prices = get_nps_prices(loc_start, loc_end)
    return nps_12plus12_hour_prices

# Tagastab -12h kuni +12h tunnihinnad km+ga + EE marginaal
def get_nps_12plus12_hour_prices_ee_marginaaliga():
    prices = get_nps_12plus12_hour_prices()
    last_30days_prices_mean = get_30days_prices_mean()
    return {
        'nps_12plus12_hour_prices': [
            {
                'y': round(el['price'] / 1000 * 100 * 1.2 + MARGINAAL, 3),
                'color': '#9E32A8' if round(el['price'] / 1000 * 100 * 1.2 + MARGINAAL, 3) > last_30days_prices_mean else 'green'
            }
            for el
            in prices
        ]
    }

# Tagastab viimase 29 põeva + 24h tuleviku keskmise tunnihinna km+ga + EE marginaal
def get_30days_prices_mean():
    now = datetime.now()
    loc_start = now.astimezone(TALLINN) - timedelta(days=29)
    loc_end = now + timedelta(days=1)
    last_30days_prices = get_nps_prices(loc_start, loc_end)
    last_30days_prices_mean = round(
        mean(
            [
                (el['price'] / 1000 * 100 * 1.2 + MARGINAAL)
                for el
                in last_30days_prices
            ]
        ), 3
    )
    return last_30days_prices_mean

if __name__ == "__main__":
    prices = get_nps_12plus12_hour_prices()
    for el in prices:
        time_start = datetime.fromtimestamp(el['timestamp'])
        price = round(el['price'] / 1000 * 100 * 1.2, 3)
        price_marginaaliga = round(price + MARGINAAL, 3)
        print(f'{time_start.day:02d} {time_start.hour:02d}', price, price_marginaaliga)
    print(get_30days_prices_mean())