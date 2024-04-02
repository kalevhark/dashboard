from datetime import datetime, timedelta
import json
import re
import time

import urllib3
# Vaigistame ssl veateated
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from bs4 import BeautifulSoup
import requests

try:
    from django.conf import settings
    from django.http import JsonResponse
    from app.models import Log
    AQUAREA_USR = settings.AQUAREA_USR
    AQUAREA_PWD = settings.AQUAREA_PWD
    accessToken = settings.AQUAREA_ACCESS_TOKEN
    selectedGwid = settings.AQUAREA_SELECTEDGWID
    selectedDeviceId = settings.AQUAREA_SELECTEDDEVICEID

except:
    import os
    import django
    # from django.test.utils import setup_test_environment
    os.environ['DJANGO_SETTINGS_MODULE'] = 'dashboard.settings'
    django.setup()
    from app.utils import dev_conf
    AQUAREA_USR = dev_conf.AQUAREA_USR
    AQUAREA_PWD = dev_conf.AQUAREA_PWD
    accessToken = dev_conf.AQUAREA_accessToken
    selectedGwid = dev_conf.AQUAREA_selectedGwid
    selectedDeviceId = dev_conf.AQUAREA_selectedDeviceId

DEBUG = False
DEGREE_CELSIUS = u'\N{DEGREE CELSIUS}'

m2rgiga = lambda i: ("+" if i > 0 else "") + str(i)

request_kwargs = {
    "login_url": "https://aquarea-smart.panasonic.com/remote/v1/api/auth/login",
    "logout_url": 'https://aquarea-smart.panasonic.com/remote/v1/api/auth/logout',
    # "headers": {
    #     "Sec-Fetch-Mode": "cors",
    #     "Origin": "https://aquarea-smart.panasonic.com",
    #     "User-Agent": "Mozilla/5.0 (iPad; CPU OS 11_0 like Mac OS X) AppleWebKit/604.1.34 (KHTML, like Gecko) Version/11.0 Mobile/15A5341f Safari/604.1",
    #     "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    #     "Accept": "*/*",
    #     "Registration-ID": "",
    #     "Referer": "https://aquarea-smart.panasonic.com/"
    # },
    "headers": {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "et-EE,et;q=0.9,en-US;q=0.8,en;q=0.7",
        # "Content-Length": "0",
        "Cookie": "; ".join(
            [
                f"accessToken={accessToken}",
                "OptanonAlertBoxClosed=2024-01-17T18:20:24.107Z",
                f"selectedGwid={selectedGwid}",
                f"selectedDeviceId={selectedDeviceId}",
                "operationDeviceTop=2",
                "OptanonConsent=isGpcEnabled=0&datestamp=Tue+Mar+19+2024+20%3A25%3A57+GMT%2B0200+(Eastern+European+Standard+Time)&version=202403.1.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=38ba5b4d-3fe3-4e80-9c8b-08b24d0fe9b9&interactionCount=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0003%3A1%2CC0002%3A1&geolocation=EE%3B81&AwaitingReconsent=false&isAnonUser=1",
                # "AWSALB=BU0xu4ht+fexZb3YWhaZC/xXFvkhR8fJGxOTXZ6GETXKsZdwEXKQ21v18jXCmPR/68EA2ujhE8wziIP1lVseDGwuIaYGcMR2Sdh/evqhqOW4eriPI8wV27hfczV+",
                # "AWSALBCORS=BU0xu4ht+fexZb3YWhaZC/xXFvkhR8fJGxOTXZ6GETXKsZdwEXKQ21v18jXCmPR/68EA2ujhE8wziIP1lVseDGwuIaYGcMR2Sdh/evqhqOW4eriPI8wV27hfczV+",
                # "JSESSIONID=FBF594569A093019A5FF85F2207EA797"
            ]
        ),
        # "Origin": "https://aquarea-smart.panasonic.com",
        "Popup-Screen-Id": "1023",
        "Referer": "https://aquarea-smart.panasonic.com/remote/a2wEnergyConsumption",
        # "Registration-Id": "",
        "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
    },
    "params": {
        "var.inputOmit": "false",
        "var.loginId": AQUAREA_USR,
        "var.password": AQUAREA_PWD
    }
}

# Tagastab hetkeaja timestamp stringina
def timestamp_now():
    return int(datetime.now().timestamp()*1000)

# Kontrollib kas logis on andmed täielikud
def check_log_dates(tarbimisandmed):
    viivitus = timedelta(seconds = 3600) # Et kindlalt täielikud andmed, siis viide 1 tund
    try:
        date_string = tarbimisandmed['dateData'][0]['startDate']
    except:
        print(tarbimisandmed)
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
def login(verbose=False):
    url = request_kwargs['login_url']
    headers = request_kwargs['headers']
    params = request_kwargs['params']
    with requests.Session() as session:
        # if verbose:
        #     print('Küsime võtme... ', end='')
        # auth_resp = session.post(
        #     url,
        #     headers=headers,
        #     params=params,
        #     verify=False
        # )
        if verbose:
            # accessToken = auth_resp.cookies['accessToken']
            # print(auth_resp, 'accessToken:', accessToken)
            print('Logime sisse... ', end='')

        login_resp = session.post(
            'https://aquarea-smart.panasonic.com/remote/contract',
            headers=headers,
            verify=False,
        )
        if verbose:
            print(login_resp)
    return session, login_resp

#
# Logib Aquarea APIst välja
#
def logout(session):
    return
    # url = request_kwargs['logout_url']
    # headers = request_kwargs['headers']
    # resp = session.post(
    #     url,
    #     headers=headers,
    #     verify=False
    # )
    # return resp

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
        session=None,
        date_string=str(datetime.now().year),
        timestamp=timestamp_now(),
        verbose=False
):
    tarbimisandmed = {}
    try:
        log_data = Log.objects.filter(data__dateString=date_string)
    except:
        log_data = None
    if log_data:
        tarbimisandmed = log_data.first().data
        if verbose:
            print(date_string, 'andmed andmebaasist')
    else:
        # Küsime andmed Aquarea APIst
        # selectedDeviceId = session.cookies['selectedDeviceId']

        # Periood liik
        date_string_splits_count = len(date_string.split('-'))
        if date_string_splits_count == 3:
            period = 'date'
        elif date_string_splits_count == 2:
            period = 'month'
        else:
            period = 'year'
        headers = request_kwargs['headers']
        resp = session.get(
            f'https://aquarea-smart.panasonic.com/remote/v1/api/consumption/{selectedDeviceId}?{period}={date_string}&_={timestamp}',
            headers = headers,
            verify=False
        )
        if verbose:
            print(date_string, resp.status_code, end=' ')
        if resp.status_code == 200:
            message = 'andmed APIst: '
            tarbimisandmed = json.loads(resp.text)
            tarbimisandmed['timestamp'] = timestamp
            tarbimisandmed['dateString'] = date_string
            if check_log_dates(tarbimisandmed):
                try:
                    # Salvestame andmed JSON formaadis
                    new_log = Log.objects.create(data=tarbimisandmed)
                    message += f'salvestame id: {new_log}'
                except:
                    message += 'ei salvesta'
            else:
                message += 'ei salvesta'
        else:
            if verbose:
                print(date_string, resp)
            message = resp.text[:200]
        if verbose:
            print(message)
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
def get_status(session=None):
    if not session:
        # Logime sisse
        session, login_resp = login(verbose=False)
        do_logout = True
    else:
        do_logout = False
    timestamp = timestamp_now()
    headers = request_kwargs['headers']
    # Küsime andmed
    # selectedDeviceId = session.cookies['selectedDeviceId']
    resp = session.get(
        f'https://aquarea-smart.panasonic.com/remote/v1/api/devices/{selectedDeviceId}?_={timestamp}',
        headers = headers,
        verify=False
    )
    try:
        status_data = json.loads(resp.text)
    except:
        print(resp.text)
        return False
    if do_logout:
        # Logime välja
        _ = logout(session)
    return status_data

# Lylitav Aquaerea mode:
# normal:  specialStatus = 0
# eco:     specialStatus = 1
# comfort: specialStatus = 2
def set_heat_specialstatus(session=None, special_mode=0, zone1delta=5, zone2delta=2, aquarea_status=None):
    status_data = None
    if not session:
        # Logime sisse
        session, login_resp = login(verbose=False)
        do_logout = True
    else:
        do_logout = False

    if not aquarea_status:
        aquarea_status = get_status(session)

    if aquarea_status and aquarea_status['errorCode'] == 0 and aquarea_status['status'][0]['operationStatus'] == 1:
        timestamp = timestamp_now()
        # Küsime andmed
        # accessToken = session.cookies['accessToken']
        # selectedDeviceId = session.cookies['selectedDeviceId']
        # selectedGwid = session.cookies['selectedGwid']
        # cookies = [
        #     f'selectedGwid={selectedGwid}',
        #     f'selectedDeviceId={selectedDeviceId}',
        #     'operationDeviceTop=1',
        #     f'accessToken={accessToken}',
        #     f'deviceControlDate={timestamp}'
        # ]
        # headers = {
        #     'Host': 'aquarea-smart.panasonic.com',
        #     'Connection': 'keep-alive',
        #     'Cache-Control': 'max-age=0',
        #     'Upgrade-Insecure-Requests': '1',
        #     'Origin': 'https://aquarea-smart.panasonic.com',
        #     'Content-Type': 'application/json;charset=UTF-8',
        #     'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.125 Mobile Safari/537.36',
        #     'Accept': 'application/json, text/javascript, */*; q=0.01',
        #     'Sec-Fetch-Site': 'same-origin',
        #     'Sec-Fetch-Mode': 'navigate',
        #     'Sec-Fetch-User': '?1',
        #     'Sec-Fetch-Dest': 'document',
        #     'Referer': 'https://aquarea-smart.panasonic.com/remote/a2wControl',
        #     'Accept-Encoding': 'gzip, deflate, br',
        #     'Accept-Language': 'et-EE,et;q=0.9,en;q=0.8,ja;q=0.7',
        #     'Cookie': ';'.join(cookies),
        # }
        headers = request_kwargs['headers']
        specialstatuses = {}

        specialstatuses[0] = {
            "status":[
                {
                    "deviceGuid":selectedDeviceId,
                    "specialStatus":0,
                    "zoneStatus":[
                        {"zoneId":1,"heatSet":0,"coolSet":0},
                        {"zoneId":2,"heatSet":0,"coolSet":0}
                    ]
                }
            ]
        }
        specialstatuses[1]  = {
            "status":[
                {
                    "deviceGuid":selectedDeviceId,
                    "specialStatus":1,
                     "zoneStatus":[
                         {"zoneId":1,"heatSet":-zone1delta,"coolSet":5},
                         {"zoneId":2,"heatSet":-zone2delta,"coolSet":5}
                     ]
                 }
            ]
        }
        specialstatuses[2] = {
            "status": [
                {
                    "deviceGuid": selectedDeviceId,
                    "specialStatus": 2,
                    "zoneStatus": [
                        {"zoneId": 1, "heatSet": zone1delta, "coolSet": -5},
                        {"zoneId": 2, "heatSet": zone2delta, "coolSet": -5}
                    ]
                }
            ]
        }
        payload = specialstatuses[special_mode]

        resp = session.post(
            f'https://aquarea-smart.panasonic.com/remote/v1/api/devices/{selectedDeviceId}',
            headers = headers,
            data = json.dumps(payload),
            verify=False
        )
        try:
            status_data = json.loads(resp.text)
        except:
            print(resp.text)
        if do_logout:
            # Logime välja
            _ = logout(session)
    return status_data

# Lylitav Aquaerea tank mode:
def set_tank_operationstatus(session=None, operation_status=0, aquarea_status=None):
    status_data = None
    if not session: # Kui sessiooni pole alustatud, logime sisse
        session, login_resp = login(verbose=False)
        do_logout = True
    else:
        do_logout = False

    if not aquarea_status:
        aquarea_status = get_status(session)

    if aquarea_status and aquarea_status['errorCode'] == 0 and aquarea_status['status'][0]['operationStatus'] == 1:
        timestamp = timestamp_now()
        # Küsime andmed
        # deviceGuid = session.cookies['selectedDeviceId']
        # accessToken = session.cookies['accessToken']
        # selectedDeviceId = session.cookies['selectedDeviceId']
        # selectedGwid = session.cookies['selectedGwid']
        # cookies = [
        #     f'selectedGwid={selectedGwid}',
        #     f'selectedDeviceId={selectedDeviceId}',
        #     'operationDeviceTop=1',
        #     f'accessToken={accessToken}',
        #     f'deviceControlDate={timestamp}'
        # ]
        # headers = {
        #     'Host': 'aquarea-smart.panasonic.com',
        #     'Connection': 'keep-alive',
        #     'Cache-Control': 'max-age=0',
        #     'Upgrade-Insecure-Requests': '1',
        #     'Origin': 'https://aquarea-smart.panasonic.com',
        #     'Content-Type': 'application/json;charset=UTF-8',
        #     'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.125 Mobile Safari/537.36',
        #     'Accept': 'application/json, text/javascript, */*; q=0.01',
        #     'Sec-Fetch-Site': 'same-origin',
        #     'Sec-Fetch-Mode': 'navigate',
        #     'Sec-Fetch-User': '?1',
        #     'Sec-Fetch-Dest': 'document',
        #     'Referer': 'https://aquarea-smart.panasonic.com/remote/a2wControl',
        #     'Accept-Encoding': 'gzip, deflate, br',
        #     'Accept-Language': 'et-EE,et;q=0.9,en;q=0.8,ja;q=0.7',
        #     'Cookie': ';'.join(cookies),
        # }
        headers = request_kwargs['headers']
        # tank temperature set:
        payload_set_tankStatus = {"status":[{"deviceGuid":selectedDeviceId,"tankStatus":[{"heatSet":45}]}]}

        payload_set_tankOperation = {
            "status": [
                {
                    "deviceGuid": selectedDeviceId,
                    "operationStatus": 1,
                    "zoneStatus": [
                        {"zoneId": 1, "operationStatus": aquarea_status['status'][0]['zoneStatus'][0]['operationStatus']},
                        {"zoneId": 2, "operationStatus": aquarea_status['status'][0]['zoneStatus'][1]['operationStatus']}
                    ],
                    "tankStatus": [{"operationStatus": operation_status}],
                    "operationMode": -1
                }
            ]
        }

        payload = payload_set_tankOperation

        resp = session.post(
            f'https://aquarea-smart.panasonic.com/remote/v1/api/devices/{selectedDeviceId}',
            headers = headers,
            data = json.dumps(payload),
            verify=False
        )
        try:
            status_data = json.loads(resp.text)
        except:
            print(resp.text)
    if do_logout:
        # Logime välja
        _ = logout(session)
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
def get_weekly_timer(session=None):
    if not session:  # Kui sessiooni pole alustatud, logime sisse
        session, login_resp = login(verbose=False)
        do_logout = True
    else:
        do_logout = False

    # Küsime andmed
    url = 'https://aquarea-smart.panasonic.com/remote/weekly_timer'
    # cookies = [
    #     f'selectedGwid={selectedGwid}',
    #     f'selectedDeviceId={selectedDeviceId}',
    #     'operationDeviceTop=1',
    #     f'accessToken={accessToken}',
    # ]
    # headers = {
    #     'Host': 'aquarea-smart.panasonic.com',
    #     'Connection': 'keep-alive',
    #     'Cache-Control': 'max-age=0',
    #     'Upgrade-Insecure-Requests': '1',
    #     'Origin': 'https://aquarea-smart.panasonic.com',
    #     'Content-Type': 'application/x-www-form-urlencoded',
    #     'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.125 Mobile Safari/537.36',
    #     'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    #     'Sec-Fetch-Site': 'same-origin',
    #     'Sec-Fetch-Mode': 'navigate',
    #     'Sec-Fetch-User': '?1',
    #     'Sec-Fetch-Dest': 'document',
    #     'Referer': 'https://aquarea-smart.panasonic.com/remote/a2wStatusDisplay',
    #     'Accept-Encoding': 'gzip, deflate, br',
    #     'Accept-Language': 'et-EE,et;q=0.9,en;q=0.8,ja;q=0.7',
    #     'Cookie': ';'.join(cookies),
    # }
    headers = request_kwargs['headers']

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
    if do_logout:
        # Logime välja
        _ = logout(session)
    return weekly_timer_data['weeklytimer'][0]['timer'] # , safe=False

# Lylitav Aquaerea mode:
# normal:  specialStatus = 0
# eco:     specialStatus = 1
# comfort: specialStatus = 2
def set_weeklytimer(session=None, mode=2):
    if not session:
        # Logime sisse
        session, login_resp = login(verbose=False)
        do_logout = True
    else:
        do_logout = False
    timestamp = timestamp_now()
    # Küsime andmed
    url = 'https://aquarea-smart.panasonic.com/remote/v1/api/data/weeklytimer/'
    # deviceGuid = session.cookies['selectedDeviceId']
    # accessToken = session.cookies['accessToken']
    # selectedDeviceId = session.cookies['selectedDeviceId']
    # selectedGwid = session.cookies['selectedGwid']
    # cookies = [
    #     f'selectedGwid={selectedGwid}',
    #     f'selectedDeviceId={selectedDeviceId}',
    #     'operationDeviceTop=1',
    #     f'accessToken={accessToken}',
    #     f'deviceControlDate={timestamp}'
    # ]
    # headers = {
    #     'Host': 'aquarea-smart.panasonic.com',
    #     'Connection': 'keep-alive',
    #     'Cache-Control': 'max-age=0',
    #     'Upgrade-Insecure-Requests': '1',
    #     'Origin': 'https://aquarea-smart.panasonic.com',
    #     'Content-Type': 'application/json;charset=UTF-8',
    #     'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.125 Mobile Safari/537.36',
    #     'Accept': 'application/json, text/javascript, */*; q=0.01',
    #     'Sec-Fetch-Site': 'same-origin',
    #     'Sec-Fetch-Mode': 'navigate',
    #     'Sec-Fetch-User': '?1',
    #     'Sec-Fetch-Dest': 'document',
    #     'Referer': 'https://aquarea-smart.panasonic.com/remote/weekly_timer',
    #     'Accept-Encoding': 'gzip, deflate, br',
    #     'Accept-Language': 'et-EE,et;q=0.9,en;q=0.8,ja;q=0.7',
    #     'Cookie': ';'.join(cookies),
    # }
    headers = request_kwargs['headers']

    # Mode [1:Tank only, 2:Heat, 3:Cool, 8:Auto, 9:Auto(Heat), 10:Auto(Cool)]
    # week 0 = esmaspäev
    weeklytimer = {
        0: [
            {'mode': mode, 'start': '00:00', 'zoneStatusHeatSet': 0, 'tankStatusHeatSet': 40},
            {'mode': mode, 'start': '07:00', 'zoneStatusHeatSet': -2, 'tankStatusHeatSet': 40},
            {'mode': mode, 'start': '16:00', 'zoneStatusHeatSet': 0, 'tankStatusHeatSet': 40},
        ],
        1: [
            {'mode': mode, 'start': '07:00', 'zoneStatusHeatSet': -2, 'tankStatusHeatSet': 40},
            {'mode': mode, 'start': '16:00', 'zoneStatusHeatSet': 0, 'tankStatusHeatSet': 40},
        ],
        2: [
            {'mode': mode, 'start': '07:00', 'zoneStatusHeatSet': -2, 'tankStatusHeatSet': 40},
            {'mode': mode, 'start': '16:00', 'zoneStatusHeatSet': 0, 'tankStatusHeatSet': 40},
        ],
        3: [
            {'mode': mode, 'start': '07:00', 'zoneStatusHeatSet': -2, 'tankStatusHeatSet': 40},
            {'mode': mode, 'start': '16:00', 'zoneStatusHeatSet': 0, 'tankStatusHeatSet': 40},
        ],
        4: [
            {'mode': mode, 'start': '07:00', 'zoneStatusHeatSet': -2, 'tankStatusHeatSet': 40},
            {'mode': mode, 'start': '16:00', 'zoneStatusHeatSet': 0, 'tankStatusHeatSet': 45},
        ],
    }

    timer = []
    for week in range(7):
        for period in range(6):
            try:
                task = weeklytimer[week][period]
                mode = task['mode']
                start = task['start']
                zoneStatusHeatSet = task['zoneStatusHeatSet']
                tankStatusHeatSet = task['tankStatusHeatSet']
                operation = 1
            except:
                mode = 0
                start = '00:00'
                zoneStatusHeatSet = 0
                tankStatusHeatSet = 0
                operation = 0

            zoneStatus = [
                {"zoneId": 1, "operationStatus": 0, "heatSet": 0, "coolSet": 0},
                {"zoneId": 2, "operationStatus": 0, "heatSet": 0, "coolSet": 0}
            ]
            tankStatus = [{"operationStatus": 0, "heatSet": 0}]

            if mode == 2:
                zoneStatus = [
                    {"zoneId": 1, "operationStatus": 1, "heatSet": zoneStatusHeatSet, "coolSet": 0},
                    {"zoneId": 2, "operationStatus": 1, "heatSet": zoneStatusHeatSet, "coolSet": 0}
                ]
                tankStatus = [{"operationStatus": 1, "heatSet": tankStatusHeatSet}]
            elif mode == 1:
                tankStatus = [{"operationStatus": 1, "heatSet": tankStatusHeatSet}]
            else:
                pass

            timer_row = {
                "week": week, "start": start, "operation": operation, "mode": mode,
                "zoneStatus": zoneStatus,
                "tankStatus": tankStatus
            }
            timer.append(timer_row)

    payload = {
        "weeklytimer": [
            {
                "timer": timer,
                "deviceGuid": selectedDeviceId,
                "operation": 1,
                "noUpdateDb": 0,
                "updateWeek": [0,1,2,3,4,5,6]
            }
        ]
    }

    # print(payload)
    # for el in payload['weeklytimer'][0]['timer']:
    #     if el['operation'] == 1:
    #         print(
    #             el['week'],
    #             el['mode'],
    #             el['start'],
    #             el['zoneStatus'][0]['heatSet'],
    #             el['zoneStatus'][1]['heatSet'],
    #             el['tankStatus'][0]['heatSet'],
    #         )

    resp = session.post(
        f'{url}{selectedDeviceId}',
        headers = headers,
        data = json.dumps(payload),
        verify=False
    )
    try:
        status_data = json.loads(resp.text)
    except:
        print(resp.text)
        return False

    if do_logout:
        _ = logout(session)
    return status_data


def update_db(year=None, month=None):
    now = datetime.now()
    year = year if year is not None else now.year
    month = month if month is not None else now.month
    dt = datetime(year, month, 1) - timedelta(days=30)
    session, _ = login()
    while dt < (datetime.now() - timedelta(days=1)):
        dateString = dt.strftime('%Y-%m-%d')
        if not Log.objects.filter(data__dateString=dateString).exists():
            consum(session=session, date_string=dateString, verbose=True)
            time.sleep(5)
        dt = dt + timedelta(days=1)

def get_hind_hour(date_string: str, consum_hour: tuple) -> int:
    pyhad = [
        datetime(2024, 2, 24),
        datetime(2024, 3, 29)
    ]
    EE_normaal = 12.56
    EE_soodus = 12.56
    EL_normaal = 8.32
    EL_soodus = 5.40
    day = datetime.strptime(date_string, '%Y-%m-%d')
    if day in pyhad: # riigipyha
        return consum_hour[1] * (EE_soodus + EL_soodus)
    if day.weekday() in [5, 6]: # L v6i P
        return consum_hour[1] * (EE_soodus + EL_soodus)
    if consum_hour[0] < 7 or consum_hour[0] >= 22:
        return consum_hour[1] * (EE_soodus + EL_soodus)
    return consum_hour[1] * (EE_normaal + EL_normaal)

def calc_consume_month(year=None, month=None):
    now = datetime.now()
    year = year if year is not None else now.year
    month = month if month is not None else now.month
    month_string = f'{year}-{month:02d}-'
    log_days = Log.objects.filter(data__dateString__startswith=month_string)
    sum_month = 0
    hind_month = 0
    for log_day in log_days:
        d = log_day.data['dateData'][0]['dataSets'][0]['data']
        for el in d:
            if el['name'] in ['Heat', 'HW']:
                sum_element = sum([hour for hour in el['values'] if hour != None])
                print(log_day.data['dateString'], el['name'], el['values'], sum_element)
                sum_month = sum_month + sum_element
                for consum_hour in enumerate(el['values']):
                    if consum_hour[1] != None:
                        hind_hour = get_hind_hour(log_day.data['dateString'], consum_hour)
                        hind_month = hind_month + hind_hour
    print(round(sum_month, 1), round(hind_month/100, 2))

if __name__ == "__main__":
    session, login_resp = login(verbose=True)
    print(login_resp)
    aquarea_status = get_status(session)
    # print(aquarea_status)
    print(json.dumps(aquarea_status, indent=4))
    # resp = set_heat_specialstatus(session=session, specialstatus=0, zone1delta=0, zone2delta=0)
    # print(resp)
    # resp = set_tank_operationstatus(
    #     session=session,
    #     operation_status=1,
    #     aquarea_status=aquarea_status
    # )
    # print(resp)
    # status = get_status(session)
    # print(status)
    # timer = weekly_timer(session)
    # print(timer)
    # con_day = consum(session, date_string='2022-03-31', verbose=True)
    # con_mon = consum(session, date_string='2021-12', verbose=True)
    # con_year = consum(session, date_string='2021', verbose=True)
    # resp = set_weeklytimer(session)
    # print(resp)
    _ = logout(session)
    # print(con_day)