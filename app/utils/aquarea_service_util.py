#!/usr/local/bin/python3
from datetime import datetime, timedelta
import json
import re
import requests
import urllib3

from bs4 import BeautifulSoup
import pytz

# Vaigistame ssl veateated
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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


def loe_logiandmed_veebist(hours=12, verbose=False):
    dateTime_last_hours = datetime.now() - timedelta(hours=hours)
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
        'var.loginId': 'kalevhark@gmail.com',
        'var.password': '130449fb1c084aed40031ba18b5fb47e',
        'var.inputOmit': 'false'
    }

    with requests.Session() as session:
        if verbose:
            print('Küsime võtmed...', end=' ')
        post = session.post(
            LOGIN_URL,
            params=params,
            verify=False
        )

        AWSALB = post.cookies['AWSALB']
        JSESSIONID = post.cookies['JSESSIONID']
        headers = {
            "Cookie": f"AWSALB={AWSALB}; JSESSIONID={JSESSIONID}"
        }

        r = session.get(REQUEST_URL)
        m = re.search("shiesuahruefutohkun = '(\S+)'", r.text)
        shiesuahruefutohkun = m.group(0).split(' = ')[1].replace("'", "")
        if verbose:
            print(shiesuahruefutohkun)

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

        items = '%2C'.join([f'{n}' for n in range(0, 71)])  # '%2C' = ','
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
        # logiandmed_raw = session.post(LOGINFO_URL, params=params, headers=headers)
        logiandmed_json = logiandmed_raw.json()

        logiandmed_dict = json.loads(logiandmed_json['logData'])
        if verbose:
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
        34,  # Actual outdoor temperature [°C]
        36,  # Outlet water temperature [°C]
        37,  # Zone1: Water temperature [°C]
        38,  # Zone2: Water temperature [°C]
        65,  # Heat mode energy consumption [kW]
        66,  # Heat mode energy generation [kW]
        69,  # Tank mode energy consumption [kW]
        70,  # Tank mode energy generation [kW]
    ]

    act_outd_temp = []
    z1_water_temp = []
    z2_water_temp = []
    heat_con = []
    # heat_gen = []
    tank_con = []
    # tank_gen = []
    tot_gen = []

    for row in logiandmed_dict:
        row_date = datetime.fromtimestamp(int(row) / 1000)
        cat_date = round((row_date - dateTime_last_hours_fullhour).seconds / 3600, 2)
        act_outd_temp.append([cat_date, float(logiandmed_dict[row][34])])
        z1_water_temp.append([cat_date, float(logiandmed_dict[row][37])])
        z2_water_temp.append([cat_date, float(logiandmed_dict[row][38])])
        heat_con_row = float(logiandmed_dict[row][65])
        heat_con.append([cat_date, heat_con_row])
        tank_con_row = float(logiandmed_dict[row][69])
        tank_con.append([cat_date, tank_con_row])
        tot_gen_row = heat_con_row + tank_con_row
        tot_gen.append([
            cat_date,
            tot_gen_row if tot_gen_row else None
        ])
        if verbose:
            print(
                cat_date,
                row_date.strftime('%H:%M'),
                [logiandmed_dict[row][el] for el in elements]
            )

    chart_data = {
        'act_outd_temp': act_outd_temp,
        'z1_water_temp': z1_water_temp,
        'z2_water_temp': z2_water_temp,
        'heat_con': heat_con,
        'tank_con': tank_con,
        'tot_gen': tot_gen
    }
    return chart_data


if __name__ == "__main__":
    data = loe_logiandmed_veebist(hours=11, verbose=True)
