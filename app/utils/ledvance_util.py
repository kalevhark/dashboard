# https://pypi.org/project/tinytuya/
import sys

try:
    from django.conf import settings
    TUYA_DEVICE_ID = settings.TUYA_DEVICE_ID
    TUYA_IP_ADDRESS = settings.TUYA_IP_ADDRESS
    TUYA_LOCAL_KEY = settings.TUYA_LOCAL_KEY
except:
    from decouple import config
    TUYA_DEVICE_ID = config('TUYA_DEVICE_ID')
    TUYA_IP_ADDRESS = config('TUYA_IP_ADDRESS')
    TUYA_LOCAL_KEY = config('TUYA_LOCAL_KEY')

import tinytuya

# Device credentials

d = tinytuya.OutletDevice(TUYA_DEVICE_ID, TUYA_IP_ADDRESS, TUYA_LOCAL_KEY)
d.set_version(3.3)

"""
DP ID	Function Point	Type	Range	Units
1	Switch 1	bool	True/False	
2	Switch 2	bool	True/False	
3	Switch 3	bool	True/False	
4	Switch 4	bool	True/False	
5	Switch 5	bool	True/False	
6	Switch 6	bool	True/False	
7	Switch 7/usb	bool	True/False	
9	Countdown 1	integer	0-86400	s
10	Countdown 2	integer	0-86400	s
11	Countdown 3	integer	0-86400	s
12	Countdown 4	integer	0-86400	s
13	Countdown 5	integer	0-86400	s
14	Countdown 6	integer	0-86400	s
15	Countdown 7	integer	0-86400	s
17	Add Electricity	integer	0-50000	kwh
18	Current	integer	0-30000	mA
19	Power	integer	0-50000	W
20	Voltage	integer	0-5000	V
21	Test Bit	integer	0-5	n/a
22	Voltage coe	integer	0-1000000	
23	Current coe	integer	0-1000000	
24	Power coe	integer	0-1000000	
25	Electricity coe	integer	0-1000000	
26	Fault	fault	ov_cr
"""

def status():
    data = d.status()
    # print('set_status() result %r' % data)
    return data

def turnon(hours=0):
    d.turn_on(switch=1)
    d.set_value(9, hours * 60 * 60)  # lülitame välja x tunni aja pärast
    # Show status and state of first controlled switch on device
    data = status()
    # print('Dictionary %r' % data)
    # print('State (bool, true is ON) %r' % data['dps']['1'])
    return data

def turnoff():
    d.turn_off(switch=1)
    # Show status and state of first controlled switch on device
    data = status()
    # print('Dictionary %r' % data)
    # print('State (bool, true is ON) %r' % data['dps']['1'])
    return data

if __name__ == '__main__':
    if len(sys.argv) > 2:
        print('You have specified too many arguments')
        sys.exit()

    if len(sys.argv) < 2:
        print('You need to specify the command: 1h 2h off')
        data = status()
        print(data)
        sys.exit()

    command = sys.argv[1]

    if command == 'off':
        turnoff()
    else:
        try:
            hours = int(command[0])
            turnon(hours=hours)
        except:
            turnoff()