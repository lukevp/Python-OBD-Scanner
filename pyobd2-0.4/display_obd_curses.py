#!/usr/bin/python

import obd
from obd.message.request import OBDRequest

import curses
import time

from serial.serialutil import SerialException

interface = None
stdscreen = None
serialPort = '/dev/ttyUSB1'

def startInterface():

	global interface

	while not interface:

		try:

			interface = obd.interface.create(serialPort, '--port')		
			interface.open()
			interface.set_protocol(None)
	
			while not interface.connected_to_vehicle:

				try:
					interface.connect_to_vehicle()
				except obd.exception.ConnectionError as ce:
					interface._flush_frames()
				except obd.exception.CommandNotSupported as cns:
					interface.close()
					interface.port.port.close()
					interface = None
				except obd.exception.ReadTimeout as rt:
					interface._flush_frames()
				except obd.exception.InterfaceError as ie:
					interface._flush_frames()

		except obd.exception.OBDException as oe:
			interface = None
			time.sleep(1)
		except obd.exception.ReadTimeout as rt:
			interface.close()
			interface.port.port.close()
			interface = None
			time.sleep(1)
		except obd.exception.InterfaceError as ie:
			interface.close()
			interface.port.port.close()
			interface = None
			time.sleep(1)
		except AttributeError as ae:
			interface = None

def displayOBDGauges():

	global interface, stdscreen
	
	mpg_counter = 0
	average_mpg = 0
	
	while True:
	
		try:
			request = obd.message.OBDRequest(sid=0x01, pid=0x05)
	
			responses = interface.send_request(request)
			stdscreen.addstr(0, 0, str((responses[0].values[0].value * 1.8) + 32.0).rjust(9, ' ') + ' deg F')
	
			request = obd.message.OBDRequest(sid=0x01, pid=0x0c)
			responses = interface.send_request(request)
			stdscreen.addstr(1, 0, str(int(round(responses[0].values[0].value))).rjust(7, ' ') + ' rpm')
	
			request = obd.message.OBDRequest(sid=0x01, pid=0x10)
			responses = interface.send_request(request)
			stdscreen.addstr(2, 0, str(round((responses[0].values[0].value * 0.0805), 3)).ljust(5, '0').rjust(11, ' ') + ' gph')
	
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
			stdscreen.addstr(3, 0, str(round(average_mpg, 3)).ljust(5, '0').rjust(11, ' ') + ' mpgc')
	
			request = obd.message.OBDRequest(sid=0x01, pid=0x42)
			responses = interface.send_request(request)
			stdscreen.addstr(4, 0, str(round(responses[0].values[0].value, 3)).ljust(6, '0').rjust(11,' ') + ' V')

			stdscreen.addstr(5, 0, str(round(velocity_kph * 0.621371)).ljust(4, '0').rjust(10, ' ') + ' MPH')

			stdscreen.refresh()

		except SerialException as se:
			interface.port.port.close()
			interface = None
			startInterface()
		except obd.exception.IntervalTimeout as ite:
			interface.close()
			interface.port.port.close()
			interface = None
		except obd.exception.ProtocolError as pe:
			interface._flush_frames()
		except obd.exception.DataError as de:
			interface._flush_frames()
		except obd.exception.CommandNotSupported as cns:
			interface._flush_frames()
		except NameError as ne:
			pass
		except ValueError as ve:
			pass
		except AttributeError as ae:
			if interface:
				interface.close()
				interface.port.port.close()
			interface = None
			startInterface()
		except AssertionError as ae:
			interface.close()
			interface.port.port.close()
			interface = None
	
def startScreen(stdscr):

	global stdscreen

	stdscreen = stdscr
	stdscreen.clear()


if __name__ == '__main__':

	startInterface()
	curses.wrapper(startScreen)
	displayOBDGauges()
	interface.disconnect_from_vehicle()
	interface.close()
