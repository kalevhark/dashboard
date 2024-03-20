#!/usr/local/bin/python3
from datetime import datetime, timedelta
import csv
import json
import re
import requests
import urllib3
# Vaigistame ssl veateated
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    from django.conf import settings
    AQUAREA_USR = settings.AQUAREA_USR
    AQUAREA_PWD_SERVICE = settings.AQUAREA_PWD_SERVICE
except:
    import os
    import django
    # from django.test.utils import setup_test_environment
    os.environ['DJANGO_SETTINGS_MODULE'] = 'dashboard.settings'
    django.setup()
    import dev_conf
    AQUAREA_USR = dev_conf.AQUAREA_USR
    AQUAREA_PWD_SERVICE = dev_conf.AQUAREA_PWD_SERVICE

import pytz

def float_or_none(datafield:str):
    try:
        return float(datafield)
    except:
        return None
#
# Aquarea Service andmete lugemine failist
#
def loe_logiandmed_failist(filename):
    with open(filename) as f:
        # andmed_raw = f.read()
        andmed_raw_dict = json.loads(f.read())
        logiandmed_raw = andmed_raw_dict['logData']
        logiandmed_dict = json.loads(logiandmed_raw)
        date_min_timestamp = int(min(logiandmed_dict.keys())) / 1000
        date_max_timestamp = int(max(logiandmed_dict.keys())) / 1000
        date_min = datetime.fromtimestamp(date_min_timestamp)
        date_max = datetime.fromtimestamp(date_max_timestamp)
        print(f'Andmed {date_min}-{date_max}')
    return logiandmed_dict


def loe_logiandmed_veebist(hours=12, verbose=True):
    dateTime_last_hours = datetime.now() - timedelta(hours=hours-1)
    dateTime_last_hours_fullhour = datetime(
        dateTime_last_hours.year,
        dateTime_last_hours.month,
        dateTime_last_hours.day,
        dateTime_last_hours.hour
    )

    LOGIN_URL = 'https://aquarea-service.panasonic.com/installer/api/auth/login'
    REQUEST_URL = 'https://aquarea-service.panasonic.com/installer/home'
    USERINFO_URL = 'https://aquarea-service.panasonic.com/installer/functionUserInformation'
    LOGINFO_URL = 'https://aquarea-service.panasonic.com/installer/api/data/log'
    LOGOUT_URL = 'https://aquarea-service.panasonic.com/installer/api/auth/logout'

    # Panasonicu kliendiparameetrid
    gwUid = '01236fba-5dc8-445a-92ff-30f6c27082c1'
    deviceId = '008007B197792584001434545313831373030634345373130434345373138313931304300000000'

    params = {
        'var.loginId': AQUAREA_USR,
        'var.password': AQUAREA_PWD_SERVICE,
        'var.inputOmit': 'false'
    }
    headers = {
        "Sec-Fetch-Mode": "cors",
        "Origin": "https://aquarea-smart.panasonic.com",
        "User-Agent": "Mozilla/5.0 (iPad; CPU OS 11_0 like Mac OS X) AppleWebKit/604.1.34 (KHTML, like Gecko) Version/11.0 Mobile/15A5341f Safari/604.1",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Accept": "*/*",
        "Registration-ID": "",
        "Referer": "https://aquarea-smart.panasonic.com/"
    }
    with requests.Session() as session:
        if verbose:
            print('Küsime võtmed...', end=' ')
        post = session.post(
            LOGIN_URL,
            params=params,
            headers=headers,
            verify=False
        )
        if verbose:
            print(post.status_code)
            print(post.text[:4000])

        AWSALB = post.cookies['AWSALB']
        AWSALBCORS = post.cookies['AWSALBCORS']
        JSESSIONID = post.cookies['JSESSIONID']
        headers["Cookie"] = f"AWSALB={AWSALB}; AWSALBCORS={AWSALBCORS}; JSESSIONID={JSESSIONID}"

        r = session.get(
            REQUEST_URL,
            headers=headers,
        )
        # print(r.status_code)
        # print(r.text[:2000])
        m = re.search("shiesuahruefutohkun = '(\S+)'", r.text)
        shiesuahruefutohkun = m.group(0).split(' = ')[1].replace("'", "")
        #if verbose:
        #    print(shiesuahruefutohkun)

        # Valime kasutaja
        payload = {
            'var.functionSelectedGwUid': gwUid
        }
        u = session.post(
            USERINFO_URL,
            data=payload,
            headers=headers,
            verify=False
        )

        if verbose:
            print('Kontrollime kasutajat (>-1)', u.text.find('Kalev'))

        # Küsime soovitud tundide logi
        logDate = int(dateTime_last_hours_fullhour.timestamp() * 1000)

        items = '%2C'.join([f'{n}' for n in range(0, 80)])  # '%2C' = ','
        logItems = '%7B%22logItems%22%3A%5B' + items + '%5D%7D'  # '{"logItems":[' + items + ']}'
        ##        params = {
        ##            'var.deviceId': deviceId,
        ##            'var.target': 0,
        ##            'var.logItems': logItems,
        ##            'var.startDate': logDate,
        ##            'shiesuahruefutohkun': shiesuahruefutohkun
        ##        }

        PARAMS = f"var.deviceId={deviceId}&var.target=0&var.startDate={logDate}&var.logItems={logItems}&shiesuahruefutohkun={shiesuahruefutohkun}"
        logiandmed_raw = session.post(
            '?'.join([LOGINFO_URL, PARAMS]),
            headers=headers
        )
        # print(logiandmed_raw.status_code)
        logiandmed_json = logiandmed_raw.json()

        logiandmed_dict = json.loads(logiandmed_json['logData'])

        if verbose:
            print('Logiandmed:', logiandmed_dict)
            mxd = int(max(logiandmed_dict.keys())) / 1000
            mnd = int(min(logiandmed_dict.keys())) / 1000
            print(f'Andmed: {datetime.fromtimestamp(mnd)}-{datetime.fromtimestamp(mxd)}, {len(logiandmed_dict)} rida')

        resp = session.post(
            LOGOUT_URL,
            headers=headers,
            verify=False)
        if verbose:
            print(resp.text)

    # Töötleme andmed graafiku jaoks
    elements = [
        41,  # Actual outdoor temperature [°C]
        42,  # Inlet water temperature [°C]
        43,  # Outlet water temperature [°C]
        44,  # Zone1: Water temperature [°C]
        45,  # Zone2: Water temperature [°C]
        72,  # Heat mode energy consumption [kW]
        74,  # Heat mode energy generation [kW]
        78,  # Tank mode energy consumption [kW]
        79,  # Tank mode energy generation [kW]
    ]

    act_outd_temp = []
    ilet_water_temp = []
    olet_water_temp = []
    z1_water_temp = []
    z2_water_temp = []
    z1_water_temp_target = []
    z2_water_temp_target = []
    tank_temp = []
    tank_temp_target = []
    heat_con = []
    heat_gen = []
    tank_con = []
    tank_gen = []
    tot_gen = []
    tot_gen_plus = []

    for row in logiandmed_dict:
        row_date = datetime.fromtimestamp(int(row) / 1000)
        # kuupäev
        cat_date = round((row_date - dateTime_last_hours_fullhour).seconds / 3600, 2)
        # välistemperatuur
        act_outd_temp.append([cat_date, float_or_none(logiandmed_dict[row][41])])
        # pumpa sisenev ja väljuv temperatuur
        ilet_water_temp.append([cat_date, float_or_none(logiandmed_dict[row][42])])
        olet_water_temp.append([cat_date, float_or_none(logiandmed_dict[row][43])])
        z1_water_temp.append([cat_date, float_or_none(logiandmed_dict[row][44])])
        z2_water_temp.append([cat_date, float_or_none(logiandmed_dict[row][45])])
        z1_water_temp_target.append([cat_date, float_or_none(logiandmed_dict[row][46])])
        z2_water_temp_target.append([cat_date, float_or_none(logiandmed_dict[row][47])])
        tank_temp.append([cat_date, float_or_none(logiandmed_dict[row][40])])
        tank_temp_target.append([cat_date, float_or_none(logiandmed_dict[row][11])])
        heat_con_row = logiandmed_dict[row][72]
        heat_con.append([cat_date, float_or_none(heat_con_row)])
        tank_con_row = logiandmed_dict[row][78]
        tank_con.append([cat_date, float_or_none(tank_con_row)])
        heat_gen_row = logiandmed_dict[row][74]
        heat_gen.append([cat_date, float_or_none(heat_gen_row)])
        tank_gen_row = logiandmed_dict[row][79]
        tank_gen.append([cat_date, float_or_none(tank_gen_row)])
        if all([float_or_none(heat_gen_row), float_or_none(tank_gen_row)]):
            tot_gen_row = float_or_none(heat_gen_row) + float_or_none(tank_gen_row)
        else:
            tot_gen_row = None
        tot_gen.append([
            cat_date,
            tot_gen_row if tot_gen_row else None
        ])
        if all([tot_gen_row, float_or_none(heat_con_row), float_or_none(tank_con_row)]):
            tot_gen_plus_row = tot_gen_row - (heat_con_row + tank_con_row)
        else:
            tot_gen_plus_row = 0
        tot_gen_plus.append([
            cat_date,
            tot_gen_plus_row if tot_gen_plus_row > 0 else None # TODO: kui on negatiivne tootlus
        ])
        if verbose:
            print(
                cat_date,
                row_date.strftime('%H:%M'),
                [logiandmed_dict[row][el] for el in elements]
            )
        status = {
            'datetime': pytz.timezone('Europe/Tallinn').localize(row_date),
            'act_outd_temp': act_outd_temp[-1][1],
            'ilet_water_temp': ilet_water_temp[-1][1],
            'olet_water_temp': olet_water_temp[-1][1],
            'z1_water_temp': z1_water_temp[-1][1],
            'z2_water_temp': z2_water_temp[-1][1],
            'z1_water_temp_target': z1_water_temp_target[-1][1],
            'z2_water_temp_target': z2_water_temp_target[-1][1],
            'tank_temp': tank_temp[-1][1],
            'tank_temp_target': tank_temp_target[-1][1]
        }

    chart_data = {
        'act_outd_temp': act_outd_temp,
        'z1_water_temp': z1_water_temp,
        'z2_water_temp': z2_water_temp,
        'heat_con': heat_con,
        'tank_con': tank_con,
        'heat_gen': heat_gen,
        'tank_gen': tank_gen,
        'tot_gen': tot_gen,
        'tot_gen_plus': tot_gen_plus,
        'status': status
    }
    return chart_data

# Tagastab statistilise küttekulu 1h kohta iga täistemperatuuri väärtuse jaoks
def get_con_per_1h(temp=0.0):
    temp = -25.0 if temp < -25.0 else temp
    temp = 20.0 if temp > 20.0 else temp
    with open(settings.STATIC_ROOT / 'app' / 'data' / 'con_per_1h.csv', newline='', ) as csvfile:
        reader = csv.DictReader(csvfile)
        con_per_1h = dict()
        for row in reader:
            con_per_1h[float(row['Actual outdoor temperature [Â°C]'])] = float(row['Heat mode energy consumption mean [kWh]'])
        # print(con_per_1h)
    return con_per_1h[round(temp, 0)]

if __name__ == "__main__":
    data = loe_logiandmed_veebist(hours=12, verbose=True)
    print(get_con_per_1h(temp=0.0))


# Parameters
"""
0 Operation [1:Off, 2:On]
1 Dry concrete [1:Off, 2:On]
2 Mode [1:Tank only, 2:Heat, 3:Cool, 8:Auto, 9:Auto(Heat), 10:Auto(Cool)]
3 Tank [1:Off, 2:On]
4 Zone1-Zone2 On-Off [1:On-Off, 2:Off-On, 3:On-On]
5 SHP control [1:Disable, 2:Enable]
6 SHP flow control (forbid ΔT) [1:Disable, 2:Enable]
7 Zone1: (water shift/water/room/pool) set temperature for heat mode [°C]
8 Zone1: (water shift/water/room) set temperature for cool mode [°C]
9 Zone2: (water shift/water/room/pool) set temperature for heat mode [°C]
10 Zone2: (water shift/water/room) set temperature for cool  mode [°C]
11 Tank water set temperature [°C]
12 Co-efficient frequency control [%]
13 Current Lv [Lv]
14 External SW [1:Close, 2:Open]
15 Heat-Cool SW [1:Heat, 2:Cool]
16 Powerful (Actual) [1:Off, 2:On]
17 Quiet (Actual) [1:Off, 2:On]
18 3-way valve [1:Room, 2:Tank]
19 Defrost (Actual) [1:Off, 2:On]
20 Room heater (Actual) [1:Off, 2:On]
21 Tank heater (Actual) [1:Off, 2:On]
22 Solar (Actual) [1:Off, 2:On]
23 Bivalent (Actual) [1:Off, 2:On]
24 Current error status [0:No error pop up screen in RC LCD, 1:Error pop up screen in RC LCD]
25 Backup heater 1 status (Actual) [1:Off, 2:On]
26 Backup heater 2 status (Actual) [1:Off, 2:On]
27 Backup heater 3 status (Actual) [1:Off, 2:On]
28 2 Zone pump 1 status (Actual) [1:Off, 2:On]
29 2 Zone pump 2 status (Actual) [1:Off, 2:On]
30 Sterilization status (Actual) [1:Off, 2:On]
31 Zone1: Actual (water outlet/room/pool) temperature [°C]
32 Zone2: Actual (water outlet/room/pool) temperature [°C]
33 Actual tank temperature [°C]
34 Actual outdoor temperature [°C]
35 Inlet water temperature [°C]
36 Outlet water temperature [°C]
37 Zone1: Water temperature [°C]
38 Zone2: Water temperature [°C]
39 Zone1: Water temperature (Target) [°C]
40 Zone2: Water temperature (Target) [°C]
41 Buffer tank: Water temperature [°C]
42 Solar: Water temperature [°C]
43 Pool: Water temperature [°C]
44 Outlet water temperature (Target) [°C]
45 Outlet 2 temperature [°C]
46 Discharge temperature [°C]
47 Room thermostat internal sensor temperature [°C]
48 Indoor piping temperature [°C]
49 Outdoor piping temperature [°C]
50 Defrost temperature [°C]
51 EVA outlet temperature [°C]
52 Bypass outlet temperature [°C]
53 IPM temperature [°C]
54 High pressure [kgf/cm2]
55 Low pressure [kgf/cm2]
56 Outdoor current [A]
57 Compressor frequency [Hz]
58 Pump flow rate [L/min]
59 Pump speed [r/min]
60 Pump duty [duty]
61 Fan motor speed 1 [r/min]
62 Fan motor speed 2 [r/min]
63 2 Zone mixing valve 1 opening [sec]
64 2 Zone mixing valve 2 opening [sec]
65 Heat mode energy consumption [kW]
66 Heat mode energy generation [kW]
67 Cool mode energy consumption [kW]
68 Cool mode energy generation [kW]
69 Tank mode energy consumption [kW]70 Tank mode energy generation [kW]
"""