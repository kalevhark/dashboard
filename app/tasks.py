#!/home/kalev/python/dashboard_env/bin/python3

#
# Aquarea soojuspumba targaks juhtimiseks
# Käivitamiseks:
# /python-env-path-to/python3 /path-to-wiki-app/tasks.py

from pathlib import Path

if __name__ == "__main__":
    import os
    import django
    from django.test.utils import setup_test_environment

    os.environ['DJANGO_SETTINGS_MODULE'] = 'dashboard.settings'
    django.setup()
    setup_test_environment()
    from django.conf import settings
    # UTIL_DIR = Path(__file__).resolve().parent  / 'utils'
    # Build paths inside the project like this: UTIL_DIR / 'subdir'.
    # print('Töökataloog:', UTIL_DIR)
else:
    from django.conf import settings
    # UTIL_DIR = settings.BASE_DIR / 'app' / 'utils'

try:
    from app import views
    from app.utils import aquarea_smart_util
except: # kui käivitatakse lokaalselt
    import views
    from utils import aquarea_smart_util

def get_special_status_predict(outdoorNow, next_hour_airtemperature):
    # Arvutame järgmise tunni aja prognoositava muutuse
    delta = round(next_hour_airtemperature - outdoorNow, 1)
    special_mode = 0
    # special_status_status = [
    #     {'specialMode': 1, 'operationStatus': 0},
    #     {'specialMode': 2, 'operationStatus': 0}
    # ]
    zone1delta = 0
    zone2delta = 0
    if delta > 2 and next_hour_airtemperature > 5: # oodata on temp t6usu -> eco
        special_mode = 1
        # special_status_status = [
        #     {'specialMode': 1, 'operationStatus': 1},
        #     {'specialMode': 2, 'operationStatus': 0}
        # ] # eco
        zone1delta = -2
        zone2delta = -1
        if delta > 4:
            zone1delta = -4
            zone2delta = -2
        if delta > 8:
            zone1delta = -6
            zone2delta = -3
    if delta < -2 and outdoorNow > 5: # oodata on temp langust -> comfort
        special_mode = 2
        # special_status_status = [
        #     {'specialMode': 1, 'operationStatus': 0},
        #     {'specialMode': 2, 'operationStatus': 1}
        # ]  # comfort
        zone1delta = 2
        zone2delta = 1
        if delta < -4:
            zone1delta = 4
            zone2delta = 2
        if delta < -8:
            zone1delta = 6
            zone2delta = 3
    special_status_status = [
        {'specialMode': 1, 'operationStatus': 1 if special_mode == 1 else 0},
        {'specialMode': 2, 'operationStatus': 1 if special_mode == 2 else 0}
    ]
    return special_status_status, special_mode, zone1delta, zone2delta

# Kas Aquearea töörežimi on vaja muuta
def change_special_status(session, aquarea_status):
    if aquarea_status and aquarea_status['errorCode'] == 0 and aquarea_status['status'][0]['operationStatus']:
        # Aquarea registreeritud välistemperatuur
        outdoorNow = aquarea_status['status'][0]['outdoorNow']
        # Ilmateenistuse registreeritud välistemperatuur
        ilm_now = views.get_ilmateenistus_now()
        # print(ilm_now)
        this_hour_airtemperature = ilm_now['airtemperature']
        # yr.no prognoositav välistemperatuur
        yrno_forecast = views.get_yrno_forecast(hours=6)
        # print(yrno_forecast)
        next_hour_airtemperature = yrno_forecast['next_12hour_outdoor_temp'][0]
        # Arvutame strateegia järgmiseks tunniks
        special_status_status, special_mode, zone1delta, zone2delta = get_special_status_predict(
            outdoorNow=outdoorNow,
            next_hour_airtemperature=next_hour_airtemperature
        )
        special_status_current = {
            'zoneStatus': aquarea_status['status'][0]['zoneStatus'],
            'specialStatus': aquarea_status['status'][0]['specialStatus'],
        }
        special_status_predict = special_status_current
        special_status_predict['zoneStatus'][0]['heatSet'] = zone1delta
        special_status_predict['zoneStatus'][1]['heatSet'] = zone2delta
        special_status_predict['specialStatus'] = special_status_status
        # kontrollime kas vaja muuta
        change = (special_status_current != special_status_predict)
        if change:
            pass # muudame midagi
        print(
            'outdoorNow', outdoorNow,
            'this_hour_airtemperature', this_hour_airtemperature,
            'next_hour_airtemperature', next_hour_airtemperature,
            'special_mode', special_mode,
            'zone1delta', zone1delta,
            'zone2delta', zone2delta,
            'change', change
        )

if __name__ == '__main__':
    session, _ = aquarea_smart_util.login()
    aquarea_status = aquarea_smart_util.get_status(session)
    # print(aquarea_status)
    change_special_status(session, aquarea_status)
    _ = aquarea_smart_util.logout(session)