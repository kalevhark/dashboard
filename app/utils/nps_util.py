from datetime import datetime, timedelta
import json
import os
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
    pass
    # import dev_conf

DEBUG = False
DEGREE_CELSIUS = u'\N{DEGREE CELSIUS}'

m2rgiga = lambda i: ("+" if i > 0 else "") + str(i)

from pytz import timezone
import pytz

import urllib3

MARGINAAL = 0.44 # senti/kWh

# Programmikataloog, mida kasutame ka varundamiseks
path = os.path.dirname(sys.argv[0])

def get_nps_12plus12_hour_prices():
    # Kuup2evad
    tallinn = timezone('Europe/Tallinn')
    utc = pytz.utc
    now = datetime.now()
    j2rgmise_t2istunni_algus = datetime(now.year, now.month, now.day, now.hour) + timedelta(seconds=60*60)
    loc_start = now.astimezone(tallinn) - timedelta(hours=12)
    loc_end = loc_start + timedelta(days=1)
    utc_start = loc_start.astimezone(utc)
    utc_end = loc_end.astimezone(utc)
    fmt = "%Y-%m-%dT%H:%M:%SZ"

    DATA_URL = 'https://dashboard.elering.ee/api/nps/price'
    params = {
        'start': utc_start.strftime(fmt),
        'end':   utc_end.strftime(fmt),
        }

    headers = {}

    csvfile_raw = requests.get(
        DATA_URL,
        params=params,
        headers=headers
        )

    content = csvfile_raw.text
    data = json.loads(content)
    nps_12plus12_hour_prices = data['data']['ee']
    return nps_12plus12_hour_prices

def get_nps_12plus12_hour_prices_ee_marginaaliga():
    prices = get_nps_12plus12_hour_prices()
    return {
        'nps_12plus12_hour_prices': [round(el['price'] / 1000 * 100 * 1.2, 3) for el in prices]
    }

if __name__ == "__main__":
    prices = get_nps_12plus12_hour_prices()
    for el in prices:
        time_start = datetime.fromtimestamp(el['timestamp'])
        price = round(el['price'] / 1000 * 100 * 1.2, 3)
        price_marginaaliga = round(price + MARGINAAL, 3)
        print(f'{time_start.day:02d} {time_start.hour:02d}', price, price_marginaaliga)