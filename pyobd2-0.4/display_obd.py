#!/usr/bin/python

import obd
from obd.message.request import OBDRequest

import time
import datetime

from serial.serialutil import SerialException

class PyOBD2:

	interface = None

	average_mpg = 0
	start_counter = None
	last_counter = None
	current_counter = None

	def __init__(self):
		self.interface = None
		self.average_mpg = 0
		self.start_counter = datetime.time()
		self.last_counter = None
		self.current_counter = self.start_counter

	def doRequest(self, sid=None, pid=None):

		if not self.interface:
			self.startInterface()

		request = obd.message.OBDRequest(sid=sid, pid=pid)
		responses = self.interface.send_request(request)

		return responses

	def resetInterface(self):

		try:
			if self.interface:
				self.interface.close()
				self.interface.port.port.close()
			self.interface = None
		except:
			print("Trying to reset empty interface.")
			self.interface = None

	def startInterface(self):

		while not self.interface:

			try:

				self.interface = obd.interface.create('/dev/ttyUSB1', '--port')		
				self.interface.open()
				self.interface.set_protocol(None)
	
				while not self.interface.connected_to_vehicle:

					try:
						self.interface.connect_to_vehicle()
					except obd.exception.ConnectionError as ce:
						print(ce)
						self.interface._flush_frames()
					except obd.exception.CommandNotSupported as cns:
						print(cns)
						self.resetInterface()
					except obd.exception.ReadTimeout as rt:
						print(rt)
						self.interface._flush_frames()
					except obd.exception.InterfaceError as ie:
						print(ie)
						self.interface._flush_frames()

			except obd.exception.OBDException as oe:
				print(oe)
				self.interface = None
				time.sleep(1)
			except obd.exception.ReadTimeout as rt:
				print(rt)
				self.resetInterface()
				time.sleep(1)
			except obd.exception.InterfaceError as ie:
				print(ie)
				self.resetInterface()
				time.sleep(1)
			except AttributeError as ae:
				print(ae)
				self.resetInterface()

	def runMonitor(self):

		return_responses = {}

		self.last_counter = self.current_counter
		self.current_counter = datetime.time()

		try:
			responses = self.doRequest(sid=0x01, pid=0x04)
			return_responses['calc_engine_load_pct'] = (
				responses[0].values[0].value
			)

			responses = self.doRequest(sid=0x01, pid=0x05)
			return_responses['engine_coolant_temp_degC'] = (
				responses[0].values[0].value 
			)
			return_responses['engine_coolant_temp_degF'] = (
				(responses[0].values[0].value * 1.8) +
				 32.0
			)

			responses = self.doRequest(sid=0x01, pid=0x0c)
			return_responses['engine_rpm'] = (
				responses[0].values[0].value
			)

			responses = self.doRequest(sid=0x01, pid=0x10)
			return_responses['maf_air_flow_rate_gps'] = (
				reponses[0].values[0].value
			)
			return_responses['engine_consumption_gph'] = (
				responses[0].values[0].value * 0.0805
			)

			responses = self.doRequest(sid=0x01, pid=0x0d)
			return_responses['velocity_kph'] = (
				responses[0].values[0].value
			)

			return_responses['instant_mpg'] = (
				return_responses['velocity_kph'] *
				7.718 /
				return_responses['maf_air_flow_rate_gps']
			)

			return_responses['mpg_total'] = (
				(
					self.average_mpg * datetime.timedelta(
						self.last_counter,
						self.start_counter
					)
				) +
				return_responses['instant_mpg'] * datetime.timedelta(
						self.current_counter,
						self.last_counter
				)
			)

			return_responses['average_mpg'] = (
				return_responses['mpg_total'] /
				datetime.timedelta(
					self.current_counter,
					self.start_counter
				)
			)

			responses = selfdoRequest(sid=0x01, pid=0x42)
			return_responses['control_module_voltage'] = (
				responses[0].values[0].value
			)

			return return_responses

		except SerialException as se:
			print(se)
			self.resetInterface()
		except obd.exception.IntervalTimeout as ite:
			print(ite)
			self.resetInterface()
		except obd.exception.ReadTimeout as rt:
			print(rt)
			self.resetInterface()
		except obd.exception.ProtocolError as pe:
			print(pe)
			self.interface._flush_frames()
		except obd.exception.DataError as de:
			print(de)
			self.interface._flush_frames()
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
			self.resetInterface()
		except AssertionError as ae:
			print(ae)
			self.resetInterface()

		return None

	def shutdown(self):
		self.interface.disconnect_from_vehicle()
		self.interface.close()
		self.resetInterface()

if __name__ == "__main__":

	pyobd2 = PyOBD2()
	pyobd2.startInterface()

	try:
		while True:
			data = pyobd2.runMonitor()
			if data:
				msg_string = (
					data['engine_coolant_temp_degF'] + 
					' deg F; ' +
					data['engine_consumption_gph'] + 
					' gph; ' +
					data['average_mpg'] +
					' mpgc; ' +
					data['control_module_voltage'] +
					' V;'
				)
				print(msg_string)
	except KeyboardInterrupt as ki:
		pass

	pyodb2.shutdown()

