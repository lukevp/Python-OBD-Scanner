#!/usr/bin/python

import obd
from obd.message.request import OBDRequest

import time
import datetime

from serial.serialutil import SerialException

class PyOBD2:

    serialport = None
    interface = None

    average_mpg = 0
    start_counter = None
    last_counter = None
    current_counter = None

    def __init__(self, serialport='/dev/ttyUSB1'):

        self.serialport = serialport
        self.interface = None

        self.average_mpg = 0
        self.start_counter = datetime.datetime.now()
        self.last_counter = None
        self.current_counter = self.start_counter

    def doRequest(self, sid=None, pid=None):

        if not self.interface:
            self.startInterface()

        request = obd.message.OBDRequest(sid=sid, pid=pid)
        responses = self.interface.send_request(request)

        return responses[0].values[0].value


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
                ser = obd.serialport.SerialPort(self.serialport)
                self.interface = obd.interface.elm.create(ser)      
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
                self.resetInterface()
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
        self.current_counter = datetime.datetime.now()

        mpg_total = None

        try:
            resp = self.doRequest(sid=0x01, pid=0x04)
            return_responses['calc_engine_load_pct'] = resp 

            resp = self.doRequest(sid=0x01, pid=0x05)
            return_responses['engine_coolant_temp_degC'] = resp
            return_responses['engine_coolant_temp_degF'] = (
                (resp * 1.8) + 32.0
            )

            resp = self.doRequest(sid=0x01, pid=0x0c)
            return_responses['engine_rpm'] = resp

            resp = self.doRequest(sid=0x01, pid=0x10)
            return_responses['maf_air_flow_rate_gps'] = resp
            return_responses['engine_consumption_gph'] = (
                resp * 0.0805
            )

            resp = self.doRequest(sid=0x01, pid=0x0d)
            return_responses['velocity_kph'] = resp

            return_responses['instant_mpg'] = (
                return_responses['velocity_kph'] *
                7.718 /
                return_responses['maf_air_flow_rate_gps']
            )

            mpg_total = (
                (
                    self.average_mpg * (
                        self.last_counter -
                        self.start_counter
                    ).total_seconds()
                ) + (
                    return_responses['instant_mpg'] * (
                        self.current_counter -
                        self.last_counter
                    ).total_seconds()
                )
            )

            self.average_mpg = (
                mpg_total /
                (
                    self.current_counter -
                    self.start_counter
                ).total_seconds()
            )
            return_responses['average_mpg'] = self.average_mpg

            resp = self.doRequest(sid=0x01, pid=0x42)
            return_responses['control_module_voltage'] = resp

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
