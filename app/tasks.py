#!/home/kalev/python/dashboard_env/bin/python3

#
# Aquarea soojuspumba targaks juhtimiseks
# Käivitamiseks:
# /python-env-path-to/python3 /path-to-wiki-app/tasks.py
import datetime
# from pathlib import Path

OUTDOOR_HEAT_EFFICENCY_TEMP = 0 # õhutemperatuur, millest alates COP>=2,9
OUTDOOR_TANK_EFFICENCY_TEMP = 5 # õhutemperatuur, millest alates COP>=1,6
OUTDOOR_TANK_GAP = 4 # millisest temperatuurilangusest alates hakatakse kütma tarbevett

if __name__ == "__main__":
    import os
    import django
    # from django.test.utils import setup_test_environment
    os.environ['DJANGO_SETTINGS_MODULE'] = 'dashboard.settings'
    django.setup()
    # setup_test_environment()
    # from django.conf import settings
    # UTIL_DIR = Path(__file__).resolve().parent  / 'utils'
    # Build paths inside the project like this: UTIL_DIR / 'subdir'.
    # print('Töökataloog:', UTIL_DIR)
# else:
    # from django.conf import settings
    # UTIL_DIR = settings.BASE_DIR / 'app' / 'utils'

try:
    from app import views
    from app.utils import aquarea_smart_util, ledvance_util
except: # kui käivitatakse lokaalselt
    import views
    from utils import aquarea_smart_util, ledvance_util

def get_special_status_predict(outdoorNow, next_hour_airtemperature):
    # Arvutame järgmise tunni aja prognoositava muutuse
    delta = round(next_hour_airtemperature - outdoorNow, 1)
    special_mode = 0
    zone1delta, zone2delta = 0, 0
    if delta > 2 and next_hour_airtemperature > OUTDOOR_HEAT_EFFICENCY_TEMP: # oodata on temp t6usu -> eco
        special_mode = 1
        zone1delta, zone2delta = -2, -1
        if delta > 4:
            zone1delta, zone2delta = -4, -2
        if delta > 8:
            zone1delta, zone2delta = -6, -3
    if delta < -2 and outdoorNow > OUTDOOR_HEAT_EFFICENCY_TEMP: # oodata on temp langust -> comfort
        special_mode = 2
        zone1delta, zone2delta = 2, 1
        if delta < -4:
            zone1delta, zone2delta = 4, 2
        if delta < -8:
            zone1delta, zone2delta = 6, 3
    special_status_status = [
        {'specialMode': 1, 'operationStatus': 1 if special_mode == 1 else 0},
        {'specialMode': 2, 'operationStatus': 1 if special_mode == 2 else 0}
    ]
    return special_status_status, special_mode, zone1delta, zone2delta

# Kas Aquearea töörežimi on vaja muuta
def change_special_status(session, aquarea_status):
    if isinstance(aquarea_status, dict) and aquarea_status['errorCode'] == 0 and aquarea_status['status'][0]['operationStatus'] == 1:
        # Aquarea registreeritud välistemperatuur
        outdoorNow = aquarea_status['status'][0]['outdoorNow']
        # Ilmateenistuse registreeritud välistemperatuur
        ilm_now = views.get_ilmateenistus_now()
        # print(ilm_now)
        this_hour_airtemperature = ilm_now.get('airtemperature')
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
        if False: # change:
            aquarea_smart_util.set_heat_specialstatus(
                session=session,
                special_mode=special_mode,
                zone1delta=zone1delta,
                zone2delta=zone2delta
            )
        special_status_dict = {
            'dt': datetime.datetime.now().strftime('%d.%m.%Y %H:%M'),
            'outdoorNow': outdoorNow,
            'this_hour_airtemperature': this_hour_airtemperature,
            'next_hour_airtemperature': next_hour_airtemperature,
            'special_mode': special_mode,
            'zone1delta': zone1delta,
            'zone2delta': zone2delta,
            'change': change
        }
        return special_status_dict

# Kas Aquearea töörežimi on vaja muuta
def change_tank_status(session, aquarea_status):
    if isinstance(aquarea_status, dict) and aquarea_status['errorCode'] == 0 and aquarea_status['status'][0]['operationStatus'] == 1:
        # Aquarea registreeritud välistemperatuur
        outdoorNow = aquarea_status['status'][0]['outdoorNow']
        tank_status_predict = 0 if outdoorNow < OUTDOOR_TANK_EFFICENCY_TEMP else 1
        tank_status_current = aquarea_status['status'][0]['tankStatus'][0]['operationStatus']
        tank_temperature_now = aquarea_status['status'][0]['tankStatus'][0]['temparatureNow']
        tank_heat_set = aquarea_status['status'][0]['tankStatus'][0]['heatSet']
        change = (tank_status_current != tank_status_predict)
        if change:
            aquarea_smart_util.set_tank_operationstatus(
                session=session,
                operation_status=tank_status_predict,
                aquarea_status=aquarea_status
            )
        tank_status_dict = {
            'dt': datetime.datetime.now().strftime('%d.%m.%Y %H:%M'),
            'outdoorNow': outdoorNow,
            'tank_status_current': tank_status_current,
            'tank_status_predict': tank_status_predict,
            'tank_temperature_now': tank_temperature_now,
            'tank_heat_set': tank_heat_set,
            'change': change
        }
        return tank_status_dict

def change_ledvance_status(aquarea_status):
    ledvance_status = ledvance_util.status()
    ledvance_on = ledvance_status['dps']['1']
    if aquarea_status and aquarea_status['errorCode'] == 0:
        # Aquarea registreeritud välistemperatuur
        outdoorNow = aquarea_status['status'][0]['outdoorNow']
        # Aquarea tank hetkenäitajad
        operation_status = aquarea_status['status'][0]['tankStatus'][0]['operationStatus']
        temperature_now = aquarea_status['status'][0]['tankStatus'][0]['temparatureNow']
        heat_set = aquarea_status['status'][0]['tankStatus'][0]['heatSet']
        heat_max = aquarea_status['status'][0]['tankStatus'][0]['heatMax']
        # Arvutame soovitud ja hetke temperatuuri erinevuse
        gap = heat_set - temperature_now
        if ledvance_on: # Kui LDV on sisselylitatud
            if temperature_now <= heat_max:
                ledvance_util.turnoff()  # lülitame ledvance v2lja
                print('LDV off')
        else: # Kui v2listemperatuur on v2iksem Aquarea tarbevee efektiivsest tootmistemperatuuris (COP < 1)
            if outdoorNow < OUTDOOR_TANK_EFFICENCY_TEMP and gap > OUTDOOR_TANK_GAP:
                ledvance_util.turnon(hours=1) # lülitame ledvance sisse
                print('LDV on=1h')

if __name__ == '__main__':
    session, _ = aquarea_smart_util.login()
    aquarea_status = aquarea_smart_util.get_status(session)
    # print(aquarea_status)
    result = change_special_status(session, aquarea_status) # normal, eco, comfort
    print('heat:', [f'{key}: {value}' for key, value in result.items()])
    result = change_tank_status(session, aquarea_status) # on, off
    print('tank:', [f'{key}: {value}' for key, value in result.items()])
    change_ledvance_status(aquarea_status) # on
    _ = aquarea_smart_util.logout(session)