from datetime import datetime, timedelta, timezone
import json

import xml.etree.ElementTree as ET

from django.http import JsonResponse
from django.shortcuts import render
import pytz

import requests

import app.utils.aquarea_service_util as aqserv
import app.utils.aquarea_smart_util as aqsmrt

DEBUG = False
DEGREE_CELSIUS = u'\N{DEGREE CELSIUS}'

m2rgiga = lambda i: ("+" if i > 0 else "") + str(i)

# Abifunktsioon numbriliste näitajate iseloomustamiseks värvikoodiga
def colorclass(temp, colorset):
    colorclass = colorset['default']
    if temp:
        for level in colorset['levels']:
            if temp > level[0]:
                colorclass = level[1]
                break
    return colorclass

def get_aquarea_serv_data(request=None):
    data = aqserv.loe_logiandmed_veebist(hours=12, verbose=False)
    return JsonResponse(data) if request else data

# Ilmateenistuse mõõtmisandmed
def get_ilmateenistus_now(request=None):
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

    airtemperature_colorset = {'default': 'blue', 'levels': [(0, 'red')]}
    ilmaandmed['airtemperature_colorclass'] = colorclass(
        ilmaandmed['airtemperature'],
        airtemperature_colorset
    )
    relativehumidity_colorset = {'default': 'red', 'levels': [(60, 'blue'), (40, 'green')]}
    ilmaandmed['relativehumidity_colorclass'] = colorclass(
        ilmaandmed['relativehumidity'],
        relativehumidity_colorset
    )

    return JsonResponse(ilmaandmed) if request else ilmaandmed

def get_yrno_forecast(request=None, hours=12):
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

        timeseries_hours = list(filter_pastnow)[:hours]

        next_12hour_outdoor_temp = [
            hour['data']['instant']['details']['air_temperature']
            # hour
            for hour
            in timeseries_hours
        ]
        next_12hour_outdoor_prec_min = [
            hour['data']['next_1_hours']['details']['precipitation_amount_min']
            for hour
            in timeseries_hours
        ]
        next_12hour_outdoor_prec_err = [
            hour['data']['next_1_hours']['details']['precipitation_amount_max'] -
            hour['data']['next_1_hours']['details']['precipitation_amount_min']
            for hour
            in timeseries_hours
        ]
        data = {
            'next_12hour_outdoor_temp': next_12hour_outdoor_temp,
            'next_12hour_outdoor_prec_min': next_12hour_outdoor_prec_min,
            'next_12hour_outdoor_prec_err': next_12hour_outdoor_prec_err
        }
        YRno_forecast.update(data)

    return JsonResponse(YRno_forecast) if request else YRno_forecast

# Andmed põrandakütte juhtseadmelt
def get_ezr_data(request=None):
    # Loeme Ilmateenistuse viimase mõõtmise andmed veebist
    href = 'http://192.168.1.205/data/static.xml'
    r = requests.get(href)
    try:
        root = ET.fromstring(r.text)
    except:
        return None

    ezr_data = dict()

    # Viimase värskenduse kuupäev
    ezr_data_datatime = root[0].find('DATETIME').text
    ezr_data['datetime'] = pytz.timezone('Europe/Tallinn')\
        .localize(datetime.fromisoformat(ezr_data_datatime))

    # Kütteahelate staatus (HEATCTRL_STATE '0'-kinni, '1'-lahti)
    for heatctrl in root.iter('HEATCTRL'):
        inuse = heatctrl.find('INUSE').text
        if inuse == '1':
            nr = heatctrl.get('nr')
            heatctrl_state = heatctrl.find('HEATCTRL_STATE').text
            # print(nr, heatctrl_state)
            ezr_data[f'nr{nr}'] = {
                'heatctrl_state': heatctrl_state
            }

    # Ruumide näitajad
    for heatarea in root.iter('HEATAREA'):
        nr = heatarea.get('nr')
        heatarea_name = heatarea.find('HEATAREA_NAME').text
        t_actual = heatarea.find('T_ACTUAL').text
        t_target = heatarea.find('T_TARGET').text
        print(nr, heatarea_name, t_actual, t_target)
        ezr_data[f'nr{nr}'].update(
            {'heatarea_name': heatarea_name,
             't_actual': t_actual,
             't_target': t_target}
        )

    return JsonResponse(ezr_data) if request else ezr_data

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
        session = aqsmrt.login()

        # Küsime andmed
        date_today_string = f'{date_today.year}-{date_today.month:02d}-{date_today.day:02d}'
        date_today_consum = aqsmrt.consum(session, period='date', date_string=date_today_string) # tänased andmed
        date_yesterday = date_today - timedelta(days=1)
        date_yesterday_string = f'{date_yesterday.year}-{date_yesterday.month:02d}-{date_yesterday.day:02d}'
        date_yesterday_consum = aqsmrt.consum(session, period='date', date_string=date_yesterday_string) # eilsed andmed
        aquarea_status_resp = aqsmrt.get_status(session) # hetkestaatus

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

    # 24h chart data
    chart_24h = index_chart24h_data(
        request,
        date_today,
        aquarea_data,
        date_today_consum,
        date_yesterday_consum,
    )

    # last 7d chart data
    date_today_last7days = {}

    if not DEBUG:
        # Logime välja
        _ = aqsmrt.logout(session)
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
        # 'date_today_last7days': date_today_last7days,
        'aquarea_data': aquarea_data,
        'chart_24h': chart_24h,
    }
    return render(request, 'app/index.html', context)


def index_chart24h_data(request, date_today, aquarea_data, date_today_consum, date_yesterday_consum):
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

    # Teeme tühja graafiku järgnevad 12h jaoks
    next_12hour_outdoor_temp = 12*[None]
    next_12hour_outdoor_prec_min = 12*[None]
    next_12hour_outdoor_prec_err = 12*[None]

    title_date = f'<strong>{date_today.strftime("%d.%m.%Y %H:%M")}</strong>'
    aquarea_temp_val = m2rgiga(aquarea_data["outdoor_now_aquarea"])
    aquarea_temp_cls = aquarea_data["outdoor_now_aquarea_colorclass"]
    title_aquarea_temp = f'<span class="color-{aquarea_temp_cls}">{aquarea_temp_val}°C</span>'
    title = ' '.join(
        [
            title_date,
            title_aquarea_temp
        ]
    )

    chart = {
        'chart': {
            'type': 'column'
        },
        'title': {
            'useHTML': True,
            'text': title
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
            'title': {
                'text': 'Kulu kW/h /Sademed mm',
            },
            'labels': {
                'format': '{value}',
                'style': {
                    'color': 'Highcharts.getOptions().colors[0]'
                }
            },
        }, { # Secondary yAxis
            'title': {
                'text': 'Välistemperatuur (Sulevi 9a)',
            },
            'labels': {
                'format': '{value}°C',
                'plotLines': [{  # zero plane
                    'value': 0,
                    'color': '#BBBBBB',
                    'width': 1,
                    'zIndex': 2
                }],
            },
            'opposite': True
        }],
        'tooltip': {
            'headerFormat': '<b>{point.x}</b><br/>',
            'pointFormat': '{series.name}: {point.y}<br/>Total: {point.stackTotal}'
        },
        # 'annotations': [{
        #     'labels': [{
        #         'point': {
        #             'x': 11 + date_today.minute/60,
        #             'xAxis': 0,
        #             'y': aquarea_temp_val,
        #             'yAxis': 0
        #         },
        #         'text': f'{aquarea_temp_val}°C'
        #     }],
        #     'labelOptions': {
        #         'backgroundColor': 'rgba(255,255,255,0.5)',
        #         'borderColor': 'silver',
        #         'style': {'fontSize': '1em'},
        #     }
        # }],
        'plotOptions': {
            'column': {
                'stacking': 'normal',
                'dataLabels': {
                    'enabled': False
                }
            }
        },
        'series': [{
            'id': 'last_12hour_outdoor_temp',
            'name': 'Välistemperatuur',
            'type': 'spline',
            'data': last_12hour_outdoor_temp, # [-7.0, -6.9, 9.5, 14.5, 18.2, 21.5, -25.2, -26.5, 23.3, 18.3, 13.9, 9.6],
            'yAxis': 1,
            'tooltip': {
                'valueSuffix': '°C'
            },
            'zIndex': 1,
            'color': '#FF3333',
            'negativeColor': '#48AFE8'
        }, {
            'id': 'next_12hour_outdoor_temp',
            'name': 'Välistemperatuur (prognoos)',
            'type': 'spline',
            'data': 12*[None] + next_12hour_outdoor_temp,
            'yAxis': 1,
            'tooltip': {
                'valueSuffix': '°C'
            },
            'zIndex': 1,
            'dashStyle': 'shortdot',
            'color': '#FF3333',
            'negativeColor': '#48AFE8'
        }, {
            'id': 'last_12hour_consum_heat',
            'name': 'Küte',
            'yAxis': 0,
            'data': last_12hour_consum_heat,
            'color': '#F5C725',
            'zIndex': 2,
        }, {
            'id': 'last_12hour_consum_tank',
            'name': 'Vesi',
            'yAxis': 0,
            'data': last_12hour_consum_tank,
            'color': '#FF8135',
            'zIndex': 2,
        }, {
            'id': 'next_12hour_outdoor_prec_err',
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
            'yAxis': 0,
            'grouping': False,
            'tooltip': {
                'valueSuffix': ' mm'
            }
	    }, {
            'id': 'next_12hour_outdoor_prec_min',
            'type': 'column',
            'name': 'Sademed (prognoos min)',
            'data': 12*[None] + next_12hour_outdoor_prec_min,
            'color': '#68CFE8',
            'yAxis': 0,
            'grouping': False,
            'tooltip': {
                'valueSuffix': ' mm'
            }
	    }, {
            'id': 'tot_gen',
            'type': 'area',
            'name': 'Küte (gen)',
            'data': [],
            'yAxis': 0,
            'zIndex': 1,
            'color': {
                'linearGradient': { 'x1': 0, 'x2': 0, 'y1': 0, 'y2': 1 },
                'stops': [
                    [0, '#00ff00'],
                    [1, '#ffffff']
                ]
            },
            'lineWidth': 1,
            'fillOpacity': 0.5,
            # 'grouping': False,
            'tooltip': {
                'valueSuffix': ' kW/h'
            }
	    }]
    }
    return chart

# def index_yrno_next12h_data(request):
#     # Järgnevad 12h
#     YRno_forecast_data = get_yrno_forecast(request, 12)
#     next_12hour_outdoor_temp = [
#         hour['data']['instant']['details']['air_temperature']
#         # hour
#         for hour
#         in YRno_forecast_data['timeseries_12h']
#     ]
#     next_12hour_outdoor_prec_min = [
#         hour['data']['next_1_hours']['details']['precipitation_amount_min']
#         for hour
#         in YRno_forecast_data['timeseries_12h']
#     ]
#     next_12hour_outdoor_prec_err = [
#         hour['data']['next_1_hours']['details']['precipitation_amount_max'] -
#         hour['data']['next_1_hours']['details']['precipitation_amount_min']
#         for hour
#         in YRno_forecast_data['timeseries_12h']
#     ]
#     data = {
#         'next_12hour_outdoor_temp': next_12hour_outdoor_temp,
#         'next_12hour_outdoor_prec_min': next_12hour_outdoor_prec_min,
#         'next_12hour_outdoor_prec_err': next_12hour_outdoor_prec_err
#     }
#     return JsonResponse(data)

# def index_ilmateenistus_now_data(request):
#     # Ilmateenistuse hetkemõõtmised
#     ilmateenistus_data = {}
#     ilmateenistus_data_resp = get_ilmateenistus_now()
#     if ilmateenistus_data_resp:
#         ilmateenistus_data['airtemperature'] = ilmateenistus_data_resp['airtemperature']
#         ilmateenistus_data['relativehumidity'] = ilmateenistus_data_resp['relativehumidity']
#         airtemperature_colorset = {'default': 'blue', 'levels': [(0, 'red')]}
#         ilmateenistus_data['airtemperature_colorclass'] = colorclass(
#             ilmateenistus_data['airtemperature'],
#             airtemperature_colorset
#         )
#         relativehumidity_colorset = {'default': 'red', 'levels': [(60, 'blue'), (40, 'green')]}
#         ilmateenistus_data['relativehumidity_colorclass'] = colorclass(
#             ilmateenistus_data['relativehumidity'],
#             relativehumidity_colorset
#         )
#     return JsonResponse(ilmateenistus_data)

# def index_aquarea_service_lasthours(request):
#     logData = aqserv.loe_logiandmed_veebist(hours=12, verbose=False)
#     return JsonResponse(logData)

# def index_get_ezr_data(request):
#     data = get_ezr_data(request)
#     return JsonResponse(data)
