from datetime import datetime, timedelta

from astral import LocationInfo
from astral import moon
from astral.geocoder import database, lookup
from astral.sun import sun
import pytz

TZ = pytz.timezone("Europe/Tallinn")

def get_location():
    l = lookup("Tallinn", database())
    print(l)

def get_sun(date=datetime.now()):
    city = LocationInfo("Valga", "Estonia", "Europe/Tallinn", 57.776944, 26.031111)

    # print((
    #     f"Information for {city.name}/{city.region}\n"
    #     f"Timezone: {city.timezone}\n"
    #     f"Latitude: {city.latitude:.02f}; Longitude: {city.longitude:.02f}\n"
    # ))

    s = sun(city.observer, date=date, tzinfo=city.timezone)
    # print((
    #     f'Dawn:    {s["dawn"]}\n'
    #     f'Sunrise: {s["sunrise"]}\n'
    #     f'Noon:    {s["noon"]}\n'
    #     f'Sunset:  {s["sunset"]}\n'
    #     f'Dusk:    {s["dusk"]}\n'
    # ))
    return s

def get_sun_UTC(date=datetime.now()):
    city = LocationInfo("Valga", "Estonia", "Europe/Tallinn", 57.776944, 26.031111)
    s = sun(city.observer, date=date)
    # print((
    #     f'Dawn:    {s["dawn"]}\n'
    #     f'Sunrise: {s["sunrise"]}\n'
    #     f'Noon:    {s["noon"]}\n'
    #     f'Sunset:  {s["sunset"]}\n'
    #     f'Dusk:    {s["dusk"]}\n'
    # ))
    return s

def get_day_or_night(date=datetime.now(tz=TZ)):
    s = get_sun(date)
    if date > s['dawn'] and date < s['dusk']:
        return 'day'
    else:
        return 'night'

class BreakOuterLoop(Exception): pass

def get_day_or_night_ranges(date=datetime.now(tz=TZ)):
    day_before = date - timedelta(days=1)
    day_after  = date + timedelta(days=1)
    date_today_range_24h = [date + timedelta(hours=n) for n in range(-11, 13)]
    range_delta = (date_today_range_24h[-1] - date_today_range_24h[0])
    range_delta_hours = range_delta.days * 24 + range_delta.seconds // 3600
    day_or_night_ranges = []
    # print(date_today_range_24h[0])
    try:
        for day in [day_before, date, day_after]:
            s = get_sun(day)
            for state in s.keys():
                state_date = s[state]
                if state_date < date_today_range_24h[0]:
                    continue
                time_delta = state_date - date_today_range_24h[0]
                time_delta_hours = time_delta.days * 24 + time_delta.seconds / 3600
                if time_delta_hours > range_delta_hours:
                    time_delta_hours = range_delta_hours
                day_or_night_ranges.append((state, time_delta_hours))
                if state_date > date_today_range_24h[-1]:
                    raise BreakOuterLoop # v2ljume m6lemast tsüklist korraga
    except BreakOuterLoop:
        pass

    day_or_night_ranges = [(day_or_night_ranges[0][0], 0)] + day_or_night_ranges
    # print(date_today_range_24h[-1])
    return day_or_night_ranges

def get_day_or_night_plotbands(date=datetime.now(tz=TZ)):
    ranges = get_day_or_night_ranges(date)
    COLORS = {
        'dawn': '#aaaaaa', # pime
        'dusk': '#dddddd', # h2mar
        'sunrise': '#dddddd' # h2mar
    }
    day_or_night_plotbands = []
    for el in range(1, len(ranges)):
        # print('from', ranges[el-1][1], 'to', ranges[el][1], ranges[el][0])
        if ranges[el][0] in COLORS.keys():
            day_or_night_plotbands.append(
                {
                    'from': ranges[el-1][1],
                    'to': ranges[el][1],
                    'color': COLORS[ranges[el][0]]
                }
            )
    return day_or_night_plotbands

def get_sun_for_year(year=2021, tz='', delta=0):
    start_hour = 9
    stop_hour = 18
    day_time_total = 0
    night_time_total = 0
    day_time_in_primetime_total = 0
    algus = datetime(year, 3, 1)
    while algus.year <= year:
        if tz == 'UTC':
            s = get_sun_UTC(algus)
        else:
            s = get_sun(algus)
        # print(algus, end=': ')
        for state in s.keys():
            if delta != 0:
                s[state] += timedelta(hours=delta)

            # print(s[state], end=' ')
        sunrise_hours = s['sunrise'].hour + s['sunrise'].minute/60 + s['sunrise'].second/3600
        sunset_hours =  s['sunset'].hour + s['sunset'].minute/60 + s['sunset'].second/3600
        day_time = sunset_hours - sunrise_hours
        day_time_in_primetime = (
            day_time -
            ((sunrise_hours-start_hour) if sunrise_hours > start_hour else 0) -
            ((stop_hour-sunset_hours) if stop_hour > sunset_hours else 0)
        )
        # print(day_time)
        day_time_total += day_time
        day_time_in_primetime_total += day_time_in_primetime
        night_time_total += (24-day_time)
        algus += timedelta(days=1)
    print(
        tz,
        delta,
        round(day_time_total, 0),
        round(night_time_total, 0),
        round(day_time_in_primetime_total, 0)
    )

def get_moon(date=datetime.now()):
    m = moon.phase(date)
    """
    0 .. 6.99	New moon
    7 .. 13.99	First quarter
    14 .. 20.99	Full moon
    21 .. 27.99	Last quarter
    """
    print(m)
    return m

def main():
    # get_location()
    # get_sun()
    # get_moon()
    # ranges = get_day_or_night_ranges()
    print(get_day_or_night())
    print(get_day_or_night_plotbands())
    get_sun_for_year(year=2021, tz='UTC', delta=2)
    get_sun_for_year(year=2021, tz='UTC', delta=3)
    get_sun_for_year(year=2021)

if __name__ == "__main__":
    main()