#!/usr/bin/python

import obd
from obd.message.request import OBDRequest

import time
from serial.serialutil import SerialException

interface = None
message_string = ''

def doRequest(sid=None, pid=None):

	if not interface:
		startInterface()

	request = obd.message.OBDRequest(sid=sid, pid=pid)
	responses = interface.send_request(request)

	return responses

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

def runMonitor():

	try:
		responses = doRequest(sid=0x01, pid=0x05)
		message_string = str((responses[0].values[0].value * 1.8) + 32.0).ljust(5, '0')[:5] + ' deg F; '

#		responses = doRequest(sid=0x01, pid=0x0c)
#		message_string += str(responses[0].values[0].value).ljust(7, '0')[:7] + ' rpm; '

		responses = doRequest(sid=0x01, pid=0x10)
		message_string += str(responses[0].values[0].value * 0.0805).ljust(5, '0')[:5] + ' gph; '

		responses = doRequest(sid=0x01, pid=0x0d)
		velocity_kph = responses[0].values[0].value
		responses = doRequest(sid=0x01, pid=0x10)
		mass_af_gps = responses[0].values[0].value
		instant_mpg = velocity_kph * 7.718 / mass_af_gps
		mpg_total = (average_mpg * mpg_counter) + instant_mpg
		mpg_counter += 1
		average_mpg = mpg_total / mpg_counter
		message_string += str(average_mpg).ljust(6, '0')[:6] + ' mpgc; '

		responses = doRequest(sid=0x01, pid=0x42)
		message_string += str(responses[0].values[0].value).ljust(5, '0')[:5] + ' V'

	except SerialException as se:

		print(se)

		interface.port.port.close()
		interface = None

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

	except AssertionError as ae:

		print(ae)

		interface.close()
		interface.port.port.close()
		interface = None

	print(message_string)

if __name__ == "__main__":

	startInterface()

	mpg_counter = 0
	average_mpg = 0

	try:
		while True:
			runMonitor()
	except KeyboardInterrupt as ki:
		pass

	interface.disconnect_from_vehicle()
	interface.close()
