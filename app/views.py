from calendar import monthrange
from datetime import datetime, timedelta, timezone
import json

import xml.etree.ElementTree as ET

from django.http import JsonResponse

from django.shortcuts import render
import pytz

import requests

import app.utils.aquarea_service_util as aqserv
import app.utils.aquarea_smart_util as aqsmrt
from app.utils.astral_util import get_day_or_night_plotbands

DEBUG = False
DEGREE_CELSIUS = u'\N{DEGREE CELSIUS}'

m2rgiga = lambda i: ("+" if i > 0 else "") + str(i)

# Tagastab kuupäeva 1 kuu tagasi
def kuu_tagasi(dt):
    year = dt.year
    if dt.month > 1:
        month = dt.month - 1
    else:
        month = 12
        year = year - 1
    if dt.day > monthrange(year, month)[1]:
        day = monthrange(year, month)[1]
    else:
        day = dt.day
    return datetime(year, month, day)

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

# Tagastab -12h kuni +12h vahemiku x-telje väärtused
def get_xaxis_categories(request=None):
    date_today = datetime.now()
    date_today_range_24h = [date_today + timedelta(hours=n) for n in range(-11, 13)]
    categories = [f'{hour.hour}' for hour in date_today_range_24h]
    return JsonResponse(categories, safe=False) if request else categories

# Ilmateenistuse mõõtmisandmed
def get_ilmateenistus_now(request=None):
    # Loeme Ilmateenistuse viimase mõõtmise andmed veebist
    jaam = 'Valga'
    href = 'http://www.ilmateenistus.ee/ilma_andmed/xml/observations.php'
    r = requests.get(href)
    try:
        root = ET.fromstring(r.text.strip())
    except:
        # Kontrollime kas vaatlusandmed ikkagi olemas
        observation_exists = r.text.find('<observations')
        if observation_exists > 0:
            root = ET.fromstring(r.text[observation_exists:])
        else:
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
    headers = {
        "User-Agent": "Mozilla/5.0 (iPad; CPU OS 11_0 like Mac OS X) AppleWebKit/604.1.34 (KHTML, like Gecko) Version/11.0 Mobile/15A5341f Safari/604.1",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Accept": "*/*",
    }
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
            actor = heatctrl.find('ACTOR').text
            actor_percent = heatctrl.find('ACTOR_PERCENT').text
            heatctrl_state = heatctrl.find('HEATCTRL_STATE').text
            ezr_data[f'nr{nr}'] = {
                'actor': actor,
                'actor_percent': actor_percent,
                'heatctrl_state': heatctrl_state
            }

    # Ruumide näitajad
    for heatarea in root.iter('HEATAREA'):
        nr = heatarea.get('nr')
        heatarea_name = heatarea.find('HEATAREA_NAME').text
        t_actual = heatarea.find('T_ACTUAL').text
        t_target = heatarea.find('T_TARGET').text
        # print(nr, heatarea_name, t_actual, t_target)
        ezr_data[f'nr{nr}'].update(
            {'heatarea_name': heatarea_name,
             't_actual': t_actual,
             't_target': t_target}
        )

    return JsonResponse(ezr_data) if request else ezr_data

# dashboardi avaleht
def index(request):
    date_today = datetime.now()
    # date_today = pytz.timezone('Europe/Tallinn').localize(date_today)
    categories = get_xaxis_categories()

    title = f'<strong>{date_today.strftime("%d.%m.%Y %H:%M")}</strong>'

    chart_24h = {
        'chart': {
            'type': 'column'
        },
        'title': {
            'useHTML': True,
            'text': title
        },
        'xAxis': {
            'categories': categories,
            'plotBands': get_day_or_night_plotbands(),
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
            'tickInterval': 1,
            'minorTickInterval': 0.5,
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
            'data': [], # last_12hour_outdoor_temp, # [-7.0, -6.9, 9.5, 14.5, 18.2, 21.5, -25.2, -26.5, 23.3, 18.3, 13.9, 9.6],
            'yAxis': 1,
            'tooltip': {
                'valueSuffix': '°C'
            },
            'zIndex': 3,
            'color': '#FF3333',
            'negativeColor': '#48AFE8'
        }, {
            'id': 'next_12hour_outdoor_temp',
            'name': 'Välistemperatuur (prognoos)',
            'type': 'spline',
            'data': [],
            'yAxis': 1,
            'tooltip': {
                'valueSuffix': '°C'
            },
            'zIndex': 1,
            'dashStyle': 'shortdot',
            'color': '#FF3333',
            'negativeColor': '#48AFE8'
        }, {
            'id': 'last_12hour_tot_gen_plus',
            'name': 'Kasu',
            'yAxis': 0,
            'pointWidth': 3,
            'data': [],
            'color': '#00ff00',
            'zIndex': 2,
            'stack': 'aquarea'
        }, {
            'id': 'last_12hour_consum_heat',
            'name': 'Küte',
            'yAxis': 0,
            'pointWidth': 3,
            'data': [], # last_12hour_consum_heat,
            'color': '#F5C725',
            'zIndex': 2,
            'stack': 'aquarea'
        }, {
            'id': 'last_12hour_consum_tank',
            'name': 'Vesi',
            'yAxis': 0,
            'pointWidth': 3,
            'data': [], # last_12hour_consum_tank,
            'color': '#FF8135',
            'zIndex': 2,
            'stack': 'aquarea'
        }, {
            'id': 'next_12hour_outdoor_prec_err',
            'type': 'column',
            'name': 'Sademed (prognoos err)',
            'data': [],
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
            'pointWidth': 20,
            'grouping': False,
            'tooltip': {
                'valueSuffix': ' mm'
            },
            'zIndex': 2,
            'stack': 'prec'
	    }, {
            'id': 'next_12hour_outdoor_prec_min',
            'type': 'column',
            'name': 'Sademed (prognoos min)',
            'data': [],
            'color': '#68CFE8',
            'yAxis': 0,
            'pointWidth': 20,
            'grouping': False,
            'tooltip': {
                'valueSuffix': ' mm'
            },
            'zIndex': 2,
            'stack': 'prec'
	    },
        ]
    }
    context = {
        # 'date_today': date_today,
        # 'date_today_last7days': date_today_last7days,
        # 'aquarea_data': aquarea_data,
        'chart_24h': chart_24h,
    }
    return render(request, 'app/index.html', context)

def get_aquarea_smrt_data(request):
    t2na = datetime.now()
    eile = t2na - timedelta(days=1)
    jooksev_aasta = t2na.year
    jooksev_kuu = t2na.month
    jooksev_p2ev = t2na.day
    kuu_eelmine = kuu_tagasi(t2na)

    # Logime sisse
    session = aqsmrt.login()

    # Hetkenäitajad
    status = aqsmrt.get_status(session)

    # Tänane kulu
    t2na_string = t2na.strftime('%Y-%m-%d')
    t2na_consum = aqsmrt.consum(session, t2na_string)
    t2na_heat = sum(filter(None, t2na_consum['dateData'][0]['dataSets'][0]['data'][0]['values']))
    t2na_tank = sum(filter(None, t2na_consum['dateData'][0]['dataSets'][0]['data'][2]['values']))

    # Eilne kulu
    eile_string = eile.strftime('%Y-%m-%d')
    eile_consum = aqsmrt.consum(session, eile_string)
    eile_heat = sum(filter(None, eile_consum['dateData'][0]['dataSets'][0]['data'][0]['values']))
    eile_tank = sum(filter(None, eile_consum['dateData'][0]['dataSets'][0]['data'][2]['values']))

    # Jooksva kuu kulu
    kuu_string = t2na.strftime('%Y-%m')
    kuu_consum = aqsmrt.consum(session, kuu_string)
    kuu_heat = sum(filter(None, kuu_consum['dateData'][0]['dataSets'][0]['data'][0]['values']))
    kuu_tank = sum(filter(None, kuu_consum['dateData'][0]['dataSets'][0]['data'][2]['values']))

    # Eelmise kuu kulu
    kuu_eelmine_string = kuu_eelmine.strftime('%Y-%m')
    kuu_eelmine_consum = aqsmrt.consum(session, kuu_eelmine_string)
    kuu_eelmine_heat = sum(filter(None, kuu_eelmine_consum['dateData'][0]['dataSets'][0]['data'][0]['values']))
    kuu_eelmine_tank = sum(filter(None, kuu_eelmine_consum['dateData'][0]['dataSets'][0]['data'][2]['values']))

    # Eelmise aasta sama kuu kulu
    kuu_aasta_tagasi_string = datetime(jooksev_aasta - 1, jooksev_kuu, 1).strftime('%Y-%m')
    kuu_aasta_tagasi_consum = aqsmrt.consum(session, kuu_aasta_tagasi_string)
    kuu_aasta_tagasi_heat = sum(
        filter(None, kuu_aasta_tagasi_consum['dateData'][0]['dataSets'][0]['data'][0]['values']))
    kuu_aasta_tagasi_tank = sum(
        filter(None, kuu_aasta_tagasi_consum['dateData'][0]['dataSets'][0]['data'][2]['values']))

    # Periood = 1.07.(aasta-1)-30.06.(aasta)
    jooksva_aasta_string = t2na.strftime('%Y')
    eelmise_aasta_string = datetime(t2na.year - 1, 1, 1).strftime('%Y')
    jooksva_aasta_consum = aqsmrt.consum(session, jooksva_aasta_string)
    eelmise_aasta_consum = aqsmrt.consum(session, eelmise_aasta_string)
    if t2na >= datetime(t2na.year, 7, 1):  # Kui kütteperioodi esimene poolaasta (alates 1. juulist)
        # Arvutame jooksva perioodi kulu
        # Jooksva perioodi 1. poolaasta küttevee kulu
        jooksva_perioodi_heat = sum(
            filter(None, jooksva_aasta_consum['dateData'][0]['dataSets'][0]['data'][0]['values'][6:]))
        # Jooksva perioodi 1. tarbevee kulu
        jooksva_perioodi_tank = sum(
            filter(None, jooksva_aasta_consum['dateData'][0]['dataSets'][0]['data'][2]['values'][6:]))
        # Arvutame eelmise perioodi kulu
        # Eelmise perioodi 1. poolaasta küttevee kulu
        eelmise_perioodi_heat = sum(
            filter(None, eelmise_aasta_consum['dateData'][0]['dataSets'][0]['data'][0]['values'][6:jooksev_kuu - 1]))
        eelmise_perioodi_heat += sum(
            filter(None, kuu_aasta_tagasi_consum['dateData'][0]['dataSets'][0]['data'][0]['values'][:jooksev_p2ev]))
        # Eelmise perioodi 1. tarbevee kulu
        eelmise_perioodi_tank = sum(
            filter(None, eelmise_aasta_consum['dateData'][0]['dataSets'][0]['data'][2]['values'][6:jooksev_kuu - 1]))
        eelmise_perioodi_tank += sum(
            filter(None, kuu_aasta_tagasi_consum['dateData'][0]['dataSets'][0]['data'][2]['values'][:jooksev_p2ev]))
    else:  # Kui kütteperioodi teine poolaasta (kuni 30. juunini)
        # Jooksva perioodi 1. poolaasta küttevee kulu
        jooksva_perioodi_heat = sum(
            filter(None, jooksva_aasta_consum['dateData'][0]['dataSets'][0]['data'][0]['values'][:7]))
        # Jooksva perioodi 1. poolaasta tarbevee kulu
        jooksva_perioodi_tank = sum(
            filter(None, jooksva_aasta_consum['dateData'][0]['dataSets'][0]['data'][2]['values'][:7]))
        # Lisame
        # Jooksva perioodi 2. poolaasta küttevee kulu
        jooksva_perioodi_heat += sum(
            filter(None, eelmise_aasta_consum['dateData'][0]['dataSets'][0]['data'][0]['values'][6:]))
        # Jooksva perioodi 2. poolaasta tarbevee kulu
        jooksva_perioodi_tank += sum(
            filter(None, eelmise_aasta_consum['dateData'][0]['dataSets'][0]['data'][2]['values'][6:]))
        # Arvutame eelmise perioodi kulu
        yle_eelmise_aasta_string = datetime(t2na.year - 2, 1, 1).strftime('%Y')
        yle_eelmise_aasta_consum = aqsmrt.consum(session, yle_eelmise_aasta_string)
        # Eelmise perioodi 1. poolaasta küttevee kulu
        eelmise_perioodi_heat = sum(
            filter(None, yle_eelmise_aasta_consum['dateData'][0]['dataSets'][0]['data'][0]['values'][6:]))
        # Eelmise perioodi 1. poolaasta tarbevee kulu
        eelmise_perioodi_tank = sum(
            filter(None, yle_eelmise_aasta_consum['dateData'][0]['dataSets'][0]['data'][2]['values'][6:]))
        # Eelmise perioodi 2. poolaasta küttevee kulu
        eelmise_perioodi_heat += sum(
            filter(None, eelmise_aasta_consum['dateData'][0]['dataSets'][0]['data'][0]['values'][:jooksev_kuu - 1]))
        eelmise_perioodi_heat += sum(
            filter(None, kuu_aasta_tagasi_consum['dateData'][0]['dataSets'][0]['data'][0]['values'][:jooksev_p2ev]))
        # Eelmise perioodi 2. poolaasta tarbevee kulu
        eelmise_perioodi_tank += sum(
            filter(None, eelmise_aasta_consum['dateData'][0]['dataSets'][0]['data'][2]['values'][:jooksev_kuu - 1]))
        eelmise_perioodi_tank += sum(
            filter(None, kuu_aasta_tagasi_consum['dateData'][0]['dataSets'][0]['data'][2]['values'][:jooksev_p2ev]))

    # Nädalagraafik
    weekly_timer = aqsmrt.weekly_timer(session)

    # Logime välja
    _ = aqsmrt.logout(session)

    # Loob 24h graafiku
    # Aquearea näitab hetketunni tarbimist - näiteks kell 00:30 näidatakse viimase poole tunni tarbimist
    # 12 viimast tundi = hetketund ja 11 eelmist
    date_today_range_24h = [t2na + timedelta(hours=n) for n in range(-11, 13)]
    categories = [f'{hour.hour}' for hour in date_today_range_24h]
    # Küsime andmed
    date_today_hour = t2na.hour
    last12_range_start, last12_range_end = 24 + date_today_hour - 11, 24 + date_today_hour + 1
    # Täna
    date_today_consum_heat = t2na_consum['dateData'][0]['dataSets'][0]['data'][0]['values']
    date_today_consum_tank = t2na_consum['dateData'][0]['dataSets'][0]['data'][2]['values']
    date_today_outdoor_temp = t2na_consum['dateData'][0]['dataSets'][2]['data'][1]['values']
    # Eile
    date_yesterday_consum_heat = eile_consum['dateData'][0]['dataSets'][0]['data'][0]['values']
    date_yesterday_consum_tank = eile_consum['dateData'][0]['dataSets'][0]['data'][2]['values']
    date_yesterday_outdoor_temp = eile_consum['dateData'][0]['dataSets'][2]['data'][1]['values']
    # Eelnevad 12h
    last_12hour_consum_heat = (date_yesterday_consum_heat + date_today_consum_heat)[last12_range_start:last12_range_end]
    last_12hour_consum_tank = (date_yesterday_consum_tank + date_today_consum_tank)[last12_range_start:last12_range_end]
    last_12hour_outdoor_temp = (date_yesterday_outdoor_temp + date_today_outdoor_temp)[
                               last12_range_start:last12_range_end]

    # Teeme tühja graafiku järgnevad 12h jaoks
    # next_12hour_outdoor_temp = 12 * [None]
    # next_12hour_outdoor_prec_min = 12 * [None]
    # next_12hour_outdoor_prec_err = 12 * [None]

    # title_date = f'<strong>{t2na.strftime("%d.%m.%Y %H:%M")}</strong>'
    # aquarea_temp_val = m2rgiga(aquarea_data["outdoor_now_aquarea"])
    # aquarea_temp_cls = aquarea_data["outdoor_now_aquarea_colorclass"]
    # title_aquarea_temp = f'<span class="color-{aquarea_temp_cls}">{aquarea_temp_val}°C</span>'
    # title = ' '.join(
    #     [
    #         title_date,
    #         title_aquarea_temp
    #     ]
    # )

    aquarea_data = {
        'status': status,
        't2na_heat': t2na_heat,
        't2na_tank': t2na_tank,
        'eile_heat': eile_heat,
        'eile_tank': eile_tank,
        'kuu_heat': kuu_heat,
        'kuu_tank': kuu_tank,
        'kuu_eelmine_heat': kuu_eelmine_heat,
        'kuu_eelmine_tank': kuu_eelmine_tank,
        'kuu_aasta_tagasi_heat': kuu_aasta_tagasi_heat,
        'kuu_aasta_tagasi_tank': kuu_aasta_tagasi_tank,
        'jooksva_perioodi_heat': jooksva_perioodi_heat,
        'jooksva_perioodi_tank': jooksva_perioodi_tank,
        'eelmise_perioodi_heat': eelmise_perioodi_heat,
        'eelmise_perioodi_tank': eelmise_perioodi_tank,
        'weekly_timer': weekly_timer,
        'last_12hour_consum_heat': last_12hour_consum_heat,
        'last_12hour_consum_tank': last_12hour_consum_tank,
        'last_12hour_outdoor_temp': last_12hour_outdoor_temp
    }
    return JsonResponse(aquarea_data)