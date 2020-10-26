from datetime import datetime, timedelta, timezone
import json
import re
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
import pytz

import requests

from .models import Log

DEBUG = False
DEGREE_CELSIUS = u'\N{DEGREE CELSIUS}'

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
def aquarea_login(request_kwargs):
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
def aquarea_logout(session, request_kwargs):
    url = request_kwargs['logout_url']
    headers = request_kwargs['headers']
    resp = session.post(
        url,
        headers=headers,
        verify=False
    )
    return resp

#
# Tagastab Aquarea hetkeoleku andmed
#
def aquarea_status(session, timestamp=timestamp_now()):
    deviceGuid = session.cookies['selectedDeviceId']
    resp = session.get(
        f'https://aquarea-smart.panasonic.com/remote/v1/api/devices/{deviceGuid}?_={timestamp}',
        verify=False
    )
    try:
        return json.loads(resp.text)
    except:
        # print(findmessage(resp.text))
        return False


#
# Tagastab Aquarea kulu
#   kasutamine: consumption(session, 'month', '2020-07', timestamp_now(), True)
# datestring valikud:
#   date=2019-08-27
#   month=2019-08
#   year=2019
#   week=2019-08-26 NB! monday = today - timedelta(days=today.weekday())
#
def aquarea_log(
        session,
        period='year',
        date_string=datetime.now().year,
        timestamp=timestamp_now(),
        # verbose=False
):
    # Küsime andmed Aquarea APIst
    deviceGuid = session.cookies['selectedDeviceId']
    resp = session.get(
        f'https://aquarea-smart.panasonic.com/remote/v1/api/consumption/{deviceGuid}?{period}={date_string}&_={timestamp}',
        verify=False
    )
    tarbimisandmed = json.loads(resp.text)
    tarbimisandmed['timestamp'] = timestamp
    tarbimisandmed['dateString'] = date_string
    if check_log_dates(tarbimisandmed):
        # Salvestame andmed JSON formaadis
        print('salvestame:', date_string, end=' id:')
        new_log = Log.objects.create(data=tarbimisandmed)
        print(new_log)
    else:
        print('ei salvesta')
    return tarbimisandmed

# KÜsib andmed Aquarea APIst
def log(request, date_string):
    log_data = Log.objects.filter(data__dateString=date_string)
    if log_data:
        tarbimisandmed = log_data.first().data
    else:
        tarbimisandmed = {}
        # Mis perioodi kohta
        if len(date_string) == 10:
            period = 'date'
        elif len(date_string) == 7:
            period = 'month'
        elif len(date_string) == 4:
            period = 'year'
        else:
            return JsonResponse(tarbimisandmed) # date_string on vigane
        # Logime sisse
        session = aquarea_login(request_kwargs)
        # Küsime andmed
        tarbimisandmed = aquarea_log(
            session,
            period=period,
            date_string=date_string
        )
        # Logime välja
        end = aquarea_logout(session, request_kwargs)
    return JsonResponse(tarbimisandmed)

# Tagastab Aquaerea hetkenäitajad
def status(request):
    # Logime sisse
    session = aquarea_login(request_kwargs)
    # Küsime andmed
    status = aquarea_status(session)
    # Logime välja
    end = aquarea_logout(session, request_kwargs)
    return JsonResponse(status)

# Tänase päeva Aquarea andmed
def today(request):
    # Logime sisse
    session = aquarea_login(request_kwargs)
    # Küsime andmed
    today = datetime.now()
    date_string = f'{today.year}-{today.month:02d}-{today.day:02d}'
    status = aquarea_log(session, period='date', date_string=date_string)
    # Logime välja
    end = aquarea_logout(session, request_kwargs)
    return JsonResponse(status)

# Tagastab Aquarea nädalagraafiku
def weekly_timer(request):
    # Logime sisse
    session = aquarea_login(request_kwargs)
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
    return JsonResponse(
        weekly_timer_data['weeklytimer'][0]['timer'],
        safe=False
    )

# Abifunktsioon numbriliste näitajate iseloomustamiseks värvikoodiga
def colorclass(temp, colorset):
    colorclass = colorset['default']
    if temp:
        for level in colorset['levels']:
            if temp > level[0]:
                colorclass = level[1]
                break
    return colorclass

# Ilmateenistuse mõõtmisandmed
def ilm_Ilmateenistus_now(request=None):
    # Loeme Ilmateenistuse viimase mõõtmise andmed veebist
    jaam = 'Valga'
    href = 'http://www.ilmateenistus.ee/ilma_andmed/xml/observations.php'
    r = requests.get(href)
    try:
        root = ET.fromstring(r.text)
    except:
        return None
    ilmaandmed = dict()
    # Mõõtmise aeg
    dt = datetime.fromtimestamp(int(root.attrib['timestamp']))
    ilmaandmed['timestamp'] = pytz.timezone('Europe/Tallinn').localize(dt)
    station = root.findall("./station/[name='"+jaam+"']")
    for el in station:
        for it in el:
            data = it.text
            # Kui ei ole tekstiväli, siis teisendame float tüübiks
            if it.tag not in ['name',
                              'station',
                              'phenomenon',
                              'phenomenon_observer']:
                try:
                    data = float(data)
                except:
                    data = None
            ilmaandmed[it.tag] = data
    return JsonResponse(ilmaandmed) if request else ilmaandmed

def ilm_YRno_forecast(request, hours):
    altitude = "64"
    lat = "57.77781"
    lon = "26.0473"
    # yr.no API
    url = 'https://api.met.no/weatherapi/locationforecast/2.0/complete'
    params = {
        'lat': lat,
        'lon': lon,
        'altitude': altitude
    }
    headers = {}
    r = requests.get(
        url,
        headers=headers,
        params=params
    )
    if r.status_code == 200:
        YRno_forecast = {
            'meta': {
                'Expires': r.headers['Expires'],
                'Last-Modified': r.headers['Last-Modified']
            },
            'data': json.loads(r.text)
        }
    else:
        YRno_forecast = {}
    if YRno_forecast:
        data = YRno_forecast['data']
        # yrno API annab uue ennustuse iga tunni aja tagant
        # alates sellele järgnevast täistunnist
        timeseries = data['properties']['timeseries']
        now = datetime.now(timezone.utc).isoformat()
        # Filtreerime hetkeajast hilisemad järgmise 48h ennustused
        filter_pastnow = filter(lambda hour: hour['time'] > now, timeseries)
        YRno_forecast['timeseries_12h'] = list(filter_pastnow)[:hours]
    return YRno_forecast

# dashboardi avaleht
def index(request):
    date_today = datetime.now()
    if DEBUG:
        # Ajutine testkuupäev
        date_today = datetime(date_today.year-1, date_today.month, date_today.day, date_today.hour, date_today.minute)
        with open('aquarea_data_cache.json', 'r') as logfile:
            aquarea_status_cache = json.loads(logfile.read())
            aquarea_status_resp = aquarea_status_cache['aquarea_status_resp']
            date_today_consum = aquarea_status_cache['date_today_consum']
            date_yesterday_consum = aquarea_status_cache['date_yesterday_consum']
    else:
        # Logime sisse
        session = aquarea_login(request_kwargs)

        # Küsime andmed
        date_today_string = f'{date_today.year}-{date_today.month:02d}-{date_today.day:02d}'
        date_today_consum = aquarea_log(session, period='date', date_string=date_today_string) # tänased andmed
        date_yesterday = date_today - timedelta(days=1)
        date_yesterday_string = f'{date_yesterday.year}-{date_yesterday.month:02d}-{date_yesterday.day:02d}'
        date_yesterday_consum = aquarea_log(session, period='date', date_string=date_yesterday_string) # eilsed andmed
        aquarea_status_resp = aquarea_status(session) # hetkestaatus

    aquarea_data = {}
    if aquarea_status_resp: # Loeme Aquearea andmed vastusest
        aquarea_status_data = aquarea_status_resp['status'][0]
        # Seadme näitajad
        aquarea_data['outdoor_now_aquarea'] = aquarea_status_data['outdoorNow']
        aquarea_data['zone1Status_temp_now'] = aquarea_status_data['zoneStatus'][0]['temparatureNow']
        aquarea_data['zone1Status_temp_set'] = aquarea_status_data['zoneStatus'][0]['heatSet']
        aquarea_data['zone1Status_operationStatus'] = aquarea_status_data['zoneStatus'][0]['operationStatus']
        aquarea_data['zone2Status_temp_now'] = aquarea_status_data['zoneStatus'][1]['temparatureNow']
        aquarea_data['zone2Status_temp_set'] = aquarea_status_data['zoneStatus'][1]['heatSet']
        aquarea_data['zone2Status_operationStatus'] = aquarea_status_data['zoneStatus'][1]['operationStatus']
        aquarea_data['tankStatus_temp_now'] = aquarea_status_data['tankStatus'][0]['temparatureNow']
        aquarea_data['tankStatus_temp_set'] = aquarea_status_data['tankStatus'][0]['heatSet']
        aquarea_data['tankStatus_operationStatus'] = aquarea_status_data['tankStatus'][0]['operationStatus']
        # värvikoodid
        outdoor_now_aquarea_colorset = {'default': 'blue', 'levels': [(0, 'red')]}
        zone1Status_temp_now_colorset = {'default': 'blue', 'levels': [(35, 'red'), (21, 'green')]}
        zone2Status_temp_now_colorset = {'default': 'blue', 'levels': [(22, 'red'), (19, 'green')]}
        tankStatus_temp_now_colorset = {'default': 'blue', 'levels': [(36, 'red'), (31, 'green')]}
        aquarea_data['outdoor_now_aquarea_colorclass'] = colorclass(
            aquarea_data['outdoor_now_aquarea'],
            outdoor_now_aquarea_colorset
        )
        aquarea_data['zone1Status_temp_now_colorclass'] = colorclass(
            aquarea_data['zone1Status_temp_now'],
            zone1Status_temp_now_colorset
        )
        aquarea_data['zone2Status_temp_now_colorclass'] = colorclass(
            aquarea_data['zone2Status_temp_now'],
            zone2Status_temp_now_colorset
        )
        aquarea_data['tankStatus_temp_now_colorclass'] = colorclass(
            aquarea_data['tankStatus_temp_now'],
            tankStatus_temp_now_colorset
        )

    # Ilmateenistuse hetkemõõtmised
    ilmateenistus_data = {}
    ilmateenistus_data_resp = ilm_Ilmateenistus_now()
    if ilmateenistus_data_resp:
        ilmateenistus_data['airtemperature'] = ilmateenistus_data_resp['airtemperature']
        ilmateenistus_data['relativehumidity'] = ilmateenistus_data_resp['relativehumidity']
        airtemperature_colorset = {'default': 'blue', 'levels': [(0, 'red')]}
        ilmateenistus_data['airtemperature_colorclass'] = colorclass(
            ilmateenistus_data['airtemperature'],
            airtemperature_colorset
        )
        relativehumidity_colorset = {'default': 'red', 'levels': [(60, 'blue'), (40, 'green')]}
        ilmateenistus_data['relativehumidity_colorclass'] = colorclass(
            ilmateenistus_data['relativehumidity'],
            relativehumidity_colorset
        )

    # yr.no ennustus
    YRno_forecast_data = ilm_YRno_forecast(request, 12)

    # 24h chart data
    chart_24h = index_chart24h_data(
        request,
        date_today,
        date_today_consum,
        date_yesterday_consum,
        YRno_forecast_data
    )

    # last 7d chart data
    date_today_last7days = {}

    if not DEBUG:
        # Logime välja
        end = aquarea_logout(session, request_kwargs)
        # Salvestame cache
        with open('aquarea_data_cache.json', 'w') as outfile:
            aquarea_status_cache = {
                'aquarea_status_resp': aquarea_status_resp,
                'date_today_consum': date_today_consum,
                'date_yesterday_consum': date_yesterday_consum
            }
            json.dump(aquarea_status_cache, outfile)

    context = {
        'date_today': date_today,
        'date_today_last7days': date_today_last7days,
        'aquarea_data': aquarea_data,
        'ilmateenistus_data': ilmateenistus_data,
        'YRno_forecast_data': YRno_forecast_data,
        'chart_24h': chart_24h,
    }
    # return JsonResponse(context)
    return render(request, 'app/index.html', context)

# dashboardi avakuva
# def index(request):
#     context = index_data(request)
#     return render(request, 'app/index.html', context)


def index_chart24h_data(request, date_today, date_today_consum, date_yesterday_consum, YRno_forecast_data):
    # Loob 24h graafiku
    # Aquearea näitab hetketunni tarbimist - näiteks kell 00:30 näidatakse viimase poole tunni tarbimist
    # 12 viimast tundi = hetketund ja 11 eelmist
    date_today_range_24h = [date_today + timedelta(hours=n) for n in range(-11, 13)]
    categories = [f'{hour.hour}' for hour in date_today_range_24h]
    # Küsime andmed
    date_today_hour = date_today.hour
    last12_range_start, last12_range_end = 24+date_today_hour-11, 24+date_today_hour+1
    # Täna
    date_today_consum_heat = date_today_consum['dateData'][0]['dataSets'][0]['data'][0]['values']
    date_today_consum_tank = date_today_consum['dateData'][0]['dataSets'][0]['data'][2]['values']
    date_today_outdoor_temp = date_today_consum['dateData'][0]['dataSets'][2]['data'][1]['values']
    # Eile
    date_yesterday_consum_heat = date_yesterday_consum['dateData'][0]['dataSets'][0]['data'][0]['values']
    date_yesterday_consum_tank = date_yesterday_consum['dateData'][0]['dataSets'][0]['data'][2]['values']
    date_yesterday_outdoor_temp = date_yesterday_consum['dateData'][0]['dataSets'][2]['data'][1]['values']
    # Eelnevad 12h
    last_12hour_consum_heat = (date_yesterday_consum_heat + date_today_consum_heat)[last12_range_start:last12_range_end]
    last_12hour_consum_tank = (date_yesterday_consum_tank + date_today_consum_tank)[last12_range_start:last12_range_end]
    last_12hour_outdoor_temp = (date_yesterday_outdoor_temp + date_today_outdoor_temp)[last12_range_start:last12_range_end]
    # Järgnevad 12h
    # YRno_forecast_data = ilm_YRno_forecast(request)
    next_12hour_outdoor_temp = 12*[None]
    # next_12hour_outdoor_temp = [
    #     hour['data']['instant']['details']['air_temperature']
    #     # hour
    #     for hour
    #     in YRno_forecast_data['timeseries_12h']
    # ]
    next_12hour_outdoor_prec_min = 12*[None]
    # next_12hour_outdoor_prec_min = [
    #     hour['data']['next_1_hours']['details']['precipitation_amount_min']
    #     for hour
    #     in YRno_forecast_data['timeseries_12h']
    # ]
    next_12hour_outdoor_prec_err = 12*[None]
    # next_12hour_outdoor_prec_err = [
    #     hour['data']['next_1_hours']['details']['precipitation_amount_max']-
    #     hour['data']['next_1_hours']['details']['precipitation_amount_min']
    #     for hour
    #     in YRno_forecast_data['timeseries_12h']
    # ]
    # next_12hour_outdoor_temp = 12 * [None] + [7.0, 6.9, 9.5, 14.5, 18.2, 21.5, 25.2, 26.5, 23.3, 18.3, 13.9, 9.6]

    chart = {
        'chart': {
            'type': 'column'
        },
        'title': {
            'text': ''
        },
        'xAxis': {
            'categories': categories,
            'plotLines': [{
                'value': 11 + date_today.minute/60,
                'label': {
                    'text': date_today.strftime("%H:%M"),
                    'style': {
                        'color': 'gray',
                        "fontSize": "10px"
                    }
                },
                'color': 'gray',
                'dashStyle': 'Dot',
                'width': 2,
                'zIndex': 3
            }]
        },
        'yAxis': [{ # Primary yAxis
            'labels': {
                'format': '{value}°C',
                'plotLines': [{  # zero plane
                    'value': 0,
                    'color': '#BBBBBB',
                    'width': 1,
                    'zIndex': 2
                }],
                'style': {
                    # 'color': 'Highcharts.getOptions().colors[1]'
                }
            },
            'title': {
                'text': 'Välistemperatuur',
                'style': {
                    # 'color': 'Highcharts.getOptions().colors[1]'
                }
            }
        }, { # Secondary yAxis
            'title': {
                'text': 'Kulu/Sademed',
                'style': {
                    # 'color': 'Highcharts.getOptions().colors[0]'
                }
            },
            'labels': {
                'format': '{value}',
                'style': {
                    'color': 'Highcharts.getOptions().colors[0]'
                }
            },
            'opposite': True
        }],
        'tooltip': {
            'headerFormat': '<b>{point.x}</b><br/>',
            'pointFormat': '{series.name}: {point.y}<br/>Total: {point.stackTotal}'
        },
        'plotOptions': {
            'column': {
                'stacking': 'normal',
                'dataLabels': {
                    'enabled': False
                }
            }
        },
        'series': [{
            'name': 'Välistemperatuur',
            'type': 'spline',
            'data': last_12hour_outdoor_temp, # [-7.0, -6.9, 9.5, 14.5, 18.2, 21.5, -25.2, -26.5, 23.3, 18.3, 13.9, 9.6],
            'tooltip': {
                'valueSuffix': '°C'
            },
            'zIndex': 1,
            'color': '#FF3333',
            'negativeColor': '#48AFE8'
        }, {
            'name': 'Välistemperatuur (prognoos)',
            'type': 'spline',
            'data': 12*[None] + next_12hour_outdoor_temp,
            'tooltip': {
                'valueSuffix': '°C'
            },
            'zIndex': 1,
            'dashStyle': 'shortdot',
            'color': '#FF3333',
            'negativeColor': '#48AFE8'
        }, {
            'name': 'Küte',
            'yAxis': 1,
            'data': last_12hour_consum_heat,
            'color': '#F5C725'
        }, {
            'name': 'Vesi',
            'yAxis': 1,
            'data': last_12hour_consum_tank,
            'color': '#FF8135'
        }, {
            'type': 'column',
            'name': 'Sademed (prognoos err)',
            'data': 12*[None] + next_12hour_outdoor_prec_err,
            'color': {
                'pattern': {
                    'path': {
                        'd': 'M 0 0 L 5 5 M 4.5 -0.5 L 5.5 0.5 M -0.5 4.5 L 0.5 5.5',
                    },
                    'width': 5,
                    'height': 5,
                    'color': '#68CFE8',
                }
            },
            'yAxis': 1,
            'grouping': False,
            'tooltip': {
                'valueSuffix': ' mm'
            }
	    }, {
            'type': 'column',
            'name': 'Sademed (prognoos min)',
            'data': 12*[None] + next_12hour_outdoor_prec_min,
            'color': '#68CFE8',
            'yAxis': 1,
            'grouping': False,
            'tooltip': {
                'valueSuffix': ' mm'
            }
	    }]
    }
    return chart

def index_yrno_next12h_data(request):
    # Järgnevad 12h
    YRno_forecast_data = ilm_YRno_forecast(request, 12)
    next_12hour_outdoor_temp = [
        hour['data']['instant']['details']['air_temperature']
        # hour
        for hour
        in YRno_forecast_data['timeseries_12h']
    ]
    next_12hour_outdoor_prec_min = [
        hour['data']['next_1_hours']['details']['precipitation_amount_min']
        for hour
        in YRno_forecast_data['timeseries_12h']
    ]
    next_12hour_outdoor_prec_err = [
        hour['data']['next_1_hours']['details']['precipitation_amount_max'] -
        hour['data']['next_1_hours']['details']['precipitation_amount_min']
        for hour
        in YRno_forecast_data['timeseries_12h']
    ]
    data = {
        'next_12hour_outdoor_temp': next_12hour_outdoor_temp,
        'next_12hour_outdoor_prec_min': next_12hour_outdoor_prec_min,
        'next_12hour_outdoor_prec_err': next_12hour_outdoor_prec_err
    }
    return JsonResponse(data)