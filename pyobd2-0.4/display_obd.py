#!/usr/bin/python

import obd
from obd.message.request import OBDRequest

import time
from serial.serialutil import SerialException

interface = None
message_string = ''

def startInterface():

	global interface

	while not interface:

		try:

			interface = obd.interface.create('/dev/ttyUSB1', '--port')		
			interface.open()
			interface.set_protocol(None)
	
			while not interface.connected_to_vehicle:

				try:
					interface.connect_to_vehicle()
				except obd.exception.ConnectionError as ce:
					print(str(ce))
					interface._flush_frames()
				except obd.exception.CommandNotSupported as cns:
					print(str(cns))
					interface.close()
					interface.port.port.close()
					interface = None
				except obd.exception.ReadTimeout as rt:
					print(str(rt))
					interface._flush_frames()
				except obd.exception.InterfaceError as ie:
					print(str(ie))
					interface._flush_frames()

		except obd.exception.OBDException as oe:
			print(str(oe))
			interface = None
			time.sleep(1)
		except obd.exception.ReadTimeout as rt:
			print(str(rt))
			interface.close()
			interface.port.port.close()
			interface = None
			time.sleep(1)
		except obd.exception.InterfaceError as ie:
			print(str(ie))
			interface.close()
			interface.port.port.close()
			interface = None
			time.sleep(1)
		except AttributeError as ae:
			print(str(ae))
			interface = None

startInterface()

mpg_counter = 0
average_mpg = 0

while True:

	try:
		request = obd.message.OBDRequest(sid=0x01, pid=0x05)

		responses = interface.send_request(request)
		message_string = str((responses[0].values[0].value * 1.8) + 32.0).ljust(5, '0')[:5] + ' deg F; '

#		request = obd.message.OBDRequest(sid=0x01, pid=0x0c)
#		responses = interface.send_request(request)
#		message_string += str(responses[0].values[0].value).ljust(7, '0')[:7] + ' rpm; '

		request = obd.message.OBDRequest(sid=0x01, pid=0x10)
		responses = interface.send_request(request)
		message_string += str(responses[0].values[0].value * 0.0805).ljust(5, '0')[:5] + ' gph; '

		request = obd.message.OBDRequest(sid=0x01, pid=0x0d)
		responses = interface.send_request(request)
		velocity_kph = responses[0].values[0].value
		request = obd.message.OBDRequest(sid=0x01, pid=0x10)
		responses = interface.send_request(request)
		mass_af_gps = responses[0].values[0].value
		instant_mpg = velocity_kph * 7.718 / mass_af_gps
		mpg_total = (average_mpg * mpg_counter) + instant_mpg
		mpg_counter += 1
		average_mpg = mpg_total / mpg_counter
		message_string += str(average_mpg).ljust(6, '0')[:6] + ' mpgc; '

		request = obd.message.OBDRequest(sid=0x01, pid=0x42)
		responses = interface.send_request(request)
		message_string += str(responses[0].values[0].value).ljust(5, '0')[:5] + ' V'

	except SerialException as se:

		print(se)

		interface.port.port.close()
		interface = None
		startInterface()

	except obd.exception.IntervalTimeout as ite:

		print(ite)

		interface.close()
		interface.port.port.close()
		interface = None

	except obd.exception.ReadTimeout as rt:

		print(rt)

		interface.close()
		interface.port.port.close()
		interface = None

	except obd.exception.ProtocolError as pe:

		print(pe)
		interface._flush_frames()

	except obd.exception.DataError as de:

		print(de)
		interface._flush_frames()

	except obd.exception.CommandNotSupported as cns:

		print(cns)
		interface._flush_frames()

	except NameError as ne:
		print(ne)
	except ValueError as ve:
		print(ve)
	except IndexError as ie:
		print(ie)
	except AttributeError as ae:
		print(ae)
		if interface:
			interface.close()
			interface.port.port.close()
		interface = None
		startInterface()
	except AssertionError as ae:
		print(ae)
		interface.close()
		interface.port.port.close()
		interface = None

	print(message_string)

interface.disconnect_from_vehicle()
interface.close()
