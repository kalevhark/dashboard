from datetime import datetime, timedelta
import json
import re

from bs4 import BeautifulSoup
from django.conf import settings
from django.http import JsonResponse
import requests

from app.models import Log

DEBUG = False
DEGREE_CELSIUS = u'\N{DEGREE CELSIUS}'

m2rgiga = lambda i: ("+" if i > 0 else "") + str(i)

request_kwargs = {
    "login_url": "https://aquarea-smart.panasonic.com/remote/v1/api/auth/login",
    "logout_url": 'https://aquarea-smart.panasonic.com/remote/v1/api/auth/logout',
    "headers": {
        "Sec-Fetch-Mode": "cors",
        "Origin": "https://aquarea-smart.panasonic.com",
        "User-Agent": "Mozilla/5.0 (iPad; CPU OS 11_0 like Mac OS X) AppleWebKit/604.1.34 (KHTML, like Gecko) Version/11.0 Mobile/15A5341f Safari/604.1",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Accept": "*/*",
        "Registration-ID": "",
        "Referer": "https://aquarea-smart.panasonic.com/"
    },
    "params": {
        "var.inputOmit": "false",
        "var.loginId": settings.AQUAREA_USR,
        "var.password": settings.AQUAREA_PWD
    }
}

# Tagastab hetkeaja timestamp stringina
def timestamp_now():
    return int(datetime.now().timestamp()*1000)

# Kontrollib kas logis on andmed täielikud
def check_log_dates(tarbimisandmed):
    viivitus = timedelta(seconds = 3600) # Et kindlalt täielikud andmed, siis viide 1 tund
    date_string = tarbimisandmed['dateData'][0]['startDate']
    timestamp = tarbimisandmed['timestamp']/1000
    periood = tarbimisandmed['dateData'][0]['timeline']['type']
    perioodi_algus = datetime.strptime(date_string, '%Y-%m-%d')
    perioodi_salvestus = datetime.fromtimestamp(timestamp)
    logi_vanus = perioodi_salvestus - perioodi_algus

    if periood == 'monthly':
        # aastaandmed
        check = (datetime(perioodi_algus.year+1, 1, 1)+viivitus < perioodi_salvestus)
    elif periood == 'daily':
        # kuuandmed
        aasta = perioodi_algus.year
        if perioodi_algus.month == 12:
            aasta += 1
            kuu = 1
        else:
            kuu = perioodi_algus.month + 1
        check = (datetime(aasta, kuu, 1)+viivitus < perioodi_salvestus)
    elif periood == 'hourly':
        # päevaandmed
         check = (perioodi_algus + timedelta(days=1)+viivitus < perioodi_salvestus)
    else:
        check = False
    # print(periood, perioodi_algus, logi_vanus)
    return check

#
# autendib kasutaja ja tagastab avatud sessiooni
#
def login():
    url = request_kwargs['login_url']
    headers = request_kwargs['headers']
    params = request_kwargs['params']
    with requests.Session() as session:
        auth_resp = session.post(
            url,
            headers=headers,
            params=params,
            verify=False
        )
        # accessToken = auth_resp.cookies['accessToken']
        # print('accessToken:', accessToken)
        login_resp = session.post(
            'https://aquarea-smart.panasonic.com/remote/contract',
            verify=False
        )
    return session

#
# Logib Aquarea APIst välja
#
def logout(session):
    url = request_kwargs['logout_url']
    headers = request_kwargs['headers']
    resp = session.post(
        url,
        headers=headers,
        verify=False
    )
    return resp

#
# Tagastab Aquarea kulu
#   kasutamine: consumption(session, '2020-07', timestamp_now(), True)
# datestring valikud:
#   date=2019-08-27
#   month=2019-08
#   year=2019
#   week=2019-08-26 NB! monday = today - timedelta(days=today.weekday()) / ei kasuta!
#
def consum(
        session,
        # period='year',
        date_string=str(datetime.now().year),
        timestamp=timestamp_now(),
        # verbose=False
):
    log_data = Log.objects.filter(data__dateString=date_string)
    if log_data:
        tarbimisandmed = log_data.first().data
        print(date_string, 'andmed andmebaasist')
    else:
        # Küsime andmed Aquarea APIst
        deviceGuid = session.cookies['selectedDeviceId']

        # Periood liik
        date_string_splits_count = len(date_string.split('-'))
        if date_string_splits_count == 3:
            period = 'date'
        elif date_string_splits_count == 2:
            period = 'month'
        else:
            period = 'year'

        resp = session.get(
            f'https://aquarea-smart.panasonic.com/remote/v1/api/consumption/{deviceGuid}?{period}={date_string}&_={timestamp}',
            verify=False
        )
        tarbimisandmed = json.loads(resp.text)
        tarbimisandmed['timestamp'] = timestamp
        tarbimisandmed['dateString'] = date_string
        print(date_string, end='')
        if check_log_dates(tarbimisandmed):
            # Salvestame andmed JSON formaadis
            new_log = Log.objects.create(data=tarbimisandmed)
            print(' salvestame id:', new_log)
        else:
            print(' ei salvesta')
        print(date_string, 'andmed APIst')
    return tarbimisandmed

# Andmebaasi korrastamine
def check_db():
    # Kustutame topeltread
    del_rows = 0
    lastSeenId = float('-Inf')
    rows = Log.objects.all().order_by('data__dateString')
    for row in rows:
        if row.data['dateString'] == lastSeenId:
            # print(row.id, row.data['dateString'])
            row.delete()
            del_rows += 1
        else:
            lastSeenId = row.data['dateString']

    session = login()

    # Kontrollime andmed koosseisu
    algus = datetime(2020, 11, 22)
    while algus < datetime.now() - timedelta(days=1):
        date_string = algus.strftime('%Y-%m-%d')
        log = Log.objects.filter(data__dateString=date_string)
        if not log:  # Andmed juba salvestatud?
            print('Hangime', date_string)
            consum(session, date_string)
            # break
        algus += timedelta(days=1)

    # y = 2020
    # for m in range(1, 11):
    #     date_string = f'{y}-{m:02}'
    #     log = Log.objects.filter(data__dateString=date_string)
    #     if not log:  # Andmed juba salvestatud?
    #         print('Hangime', date_string)
    #         consum(session, date_string)

    _ = logout(session)

    data = {
        'del_rows': del_rows,
    }

    print(data)
    return JsonResponse(data)


# KÜsib andmed Aquarea APIst
def log(request, date_string):
    log_data = Log.objects.filter(data__dateString=date_string)
    print(date_string, end='')
    if log_data:
        tarbimisandmed = log_data.first().data
        print(' andmed andmebaasist')
    else:
        tarbimisandmed = {}

        # Logime sisse
        session = login()
        # Küsime andmed
        tarbimisandmed = consum(
            session,
            date_string=date_string
        )
        # Logime välja
        _ = logout(session)
        print(' andmed APIst')
    return JsonResponse(tarbimisandmed)

# Tagastab Aquaerea hetkenäitajad
def get_status(session):
    # Logime sisse
    # session = login()
    timestamp = timestamp_now()
    # Küsime andmed
    deviceGuid = session.cookies['selectedDeviceId']
    resp = session.get(
        f'https://aquarea-smart.panasonic.com/remote/v1/api/devices/{deviceGuid}?_={timestamp}',
        verify=False
    )
    try:
        status_data = json.loads(resp.text)
    except:
        # print(findmessage(resp.text))
        return False

    # Logime välja
    # _ = logout(session)
    return status_data

# # Tänase päeva Aquarea andmed
# def today(request=None):
#     # Logime sisse
#     session = login()
#     # Küsime andmed
#     today = datetime.now()
#     date_string = f'{today.year}-{today.month:02d}-{today.day:02d}'
#     status = consum(session, date_string=date_string)
#     # Logime välja
#     end = logout(session)
#     return JsonResponse(status)

# Tagastab Aquarea nädalagraafiku
def weekly_timer(session=None):
    # Logime sisse
    # session = login()

    # Küsime andmed
    url = 'https://aquarea-smart.panasonic.com/remote/weekly_timer'
    accessToken = session.cookies['accessToken']
    selectedDeviceId = session.cookies['selectedDeviceId']
    selectedGwid = session.cookies['selectedGwid']
    cookies = [
        f'selectedGwid={selectedGwid}',
        f'selectedDeviceId={selectedDeviceId}',
        'operationDeviceTop=1',
        f'accessToken={accessToken}',
    ]
    headers = {
        'Host': 'aquarea-smart.panasonic.com',
        'Connection': 'keep-alive',
        'Cache-Control': 'max-age=0',
        'Upgrade-Insecure-Requests': '1',
        'Origin': 'https://aquarea-smart.panasonic.com',
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.125 Mobile Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-User': '?1',
        'Sec-Fetch-Dest': 'document',
        'Referer': 'https://aquarea-smart.panasonic.com/remote/a2wStatusDisplay',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'et-EE,et;q=0.9,en;q=0.8,ja;q=0.7',
        'Cookie': ';'.join(cookies),
    }

    # Küsime nädalaseadistuse andmed
    resp = session.post(
        url,
        headers=headers,
        verify=False
    )
    # Otsime üles <script> tagid, kus on nädalaseadistuse andmed
    soup = BeautifulSoup(resp.text, 'html.parser')
    scripts = soup.find_all('script')
    substr = 'weeklyTimerInfo'

    for script in scripts:
        if script.string and (script.string.find(substr) > 0):
            weekly_timer_script = script.string
            break
    splits = weekly_timer_script.string.split(';')

    for split in splits:
        if split.find(substr) > 0:
            weekly_timer_split = split
            break

    # Leiame stringi, mis on ('( ja )') vahel
    raw_data_string = re.search(r"\(\'\((.*?)\)\'\)", weekly_timer_split).group(1)
    # Puhastame '\' sümbolitest
    raw_data_string = raw_data_string.replace('\\', '')

    # Teisendame sringist jsoni nädalaseadistuse andmed
    weekly_timer_data = json.loads(raw_data_string)

    return weekly_timer_data['weeklytimer'][0]['timer'] # , safe=False
