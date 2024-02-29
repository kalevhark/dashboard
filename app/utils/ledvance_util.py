# https://pypi.org/project/tinytuya/
import sys

try:
    from django.conf import settings
    TUYA_DEVICE_ID = settings.TUYA_DEVICE_ID
    TUYA_IP_ADDRESS = settings.TUYA_IP_ADDRESS
    TUYA_LOCAL_KEY = settings.TUYA_LOCAL_KEY
    TUYA_DEVICE_ID_2 = settings.TUYA_DEVICE_ID_2
    TUYA_IP_ADDRESS_2 = settings.TUYA_IP_ADDRESS_2
    TUYA_LOCAL_KEY_2 = settings.TUYA_LOCAL_KEY_2
except:
    import dev_conf
    TUYA_DEVICE_ID = dev_conf.TUYA_DEVICE_ID
    TUYA_IP_ADDRESS = dev_conf.TUYA_IP_ADDRESS
    TUYA_LOCAL_KEY = dev_conf.TUYA_LOCAL_KEY
    TUYA_DEVICE_ID_2 = dev_conf.TUYA_DEVICE_ID_2
    TUYA_IP_ADDRESS_2 = dev_conf.TUYA_IP_ADDRESS_2
    TUYA_LOCAL_KEY_2 = dev_conf.TUYA_LOCAL_KEY_2
    # from decouple import config
    # TUYA_DEVICE_ID = config('TUYA_DEVICE_ID')
    # TUYA_IP_ADDRESS = config('TUYA_IP_ADDRESS')
    # TUYA_LOCAL_KEY = config('TUYA_LOCAL_KEY')

import tinytuya

# Device credentials


ledvance_1 = tinytuya.OutletDevice(TUYA_DEVICE_ID, TUYA_IP_ADDRESS, TUYA_LOCAL_KEY)
ledvance_1.set_version(3.3)
ledvance_2 = tinytuya.OutletDevice(TUYA_DEVICE_ID_2, TUYA_IP_ADDRESS_2, TUYA_LOCAL_KEY_2)
ledvance_2.set_version(3.3)

d = {
    1: ledvance_1, # boiler
    2: ledvance_2 # j6uluvalgus
}
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

38 Relay status off/on/memory
"""

def status(ledvance=1):
    data = d[ledvance].status()
    # print('set_status() result %r' % data)
    return data

def countdown(ledvance=1, seconds=0):
    d[ledvance].set_value(9, seconds)
    data = status(ledvance)
    return data

def turnon(ledvance=1, hours=0):
    d[ledvance].turn_on(switch=1)
    d[ledvance].set_value(9, hours * 60 * 60)  # lülitame välja x tunni aja pärast
    # Show status and state of first controlled switch on device
    data = status(ledvance)
    # print('Dictionary %r' % data)
    # print('State (bool, true is ON) %r' % data['dps']['1'])
    return data

def turnoff(ledvance=1):
    d[ledvance].turn_off(switch=1)
    # Show status and state of first controlled switch on device
    data = status(ledvance)
    # print('Dictionary %r' % data)
    # print('State (bool, true is ON) %r' % data['dps']['1'])
    return data

if __name__ == '__main__':
    ledvance = 2
    if len(sys.argv) > 2:
        print('You have specified too many arguments')
        sys.exit()

    if len(sys.argv) < 2:
        print('You need to specify the command: 1h 2h off')
        data = status(ledvance)
        # data = countdown(ledvance, seconds=10)
        print(data)
        sys.exit()

    command = sys.argv[1]

    if command == 'off':
        turnoff(ledvance)
    else:
        try:
            hours = int(command[0])
            turnon(ledvance, hours=hours)
        except:
            turnoff(ledvance)