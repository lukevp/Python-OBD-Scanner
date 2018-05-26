#!/usr/bin/python

import tkFont
import Tkinter as tk

import obd
from obd.message.request import OBDRequest

import time

serialPort = '/dev/ttyUSB1'

class Application(tk.Frame):
        
        interface = None

        mpg_counter = 0
        average_mpg = 0

    def __init__(self):

        self.root = tk.Tk()

        self.root.rowconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=1)
        self.root.columnconfigure(2, weight=1)

        self.font = tkFont.Font(size=36)

        tk.Frame.__init__(self, self.root)

        self.root.grid()
        self.createWidgets()
        self.startInterface()

    def createWidgets(self):

        self.oneLabelVar = tk.StringVar()
        self.twoLabelVar = tk.StringVar()
        self.threeLabelVar = tk.StringVar()
        self.fourLabelVar = tk.StringVar()
        self.fiveLabelVar = tk.StringVar()
        self.sixLabelVar = tk.StringVar()

        self.oneLabel = tk.Label(
            self.root,
            font=self.font,
            relief=tk.SUNKEN,
            textvariable=self.oneLabelVar
        )
        self.oneLabel.grid(
            row=0,
            column=0,
            sticky=tk.N+tk.S+tk.E+tk.W
        )
        self.oneLabelVar.set('1')

        self.twoLabel = tk.Label(
            self.root,
            font=self.font,
            relief=tk.SUNKEN,
            textvariable=self.twoLabelVar
        )
        self.twoLabel.grid(
            row=0,
            column=1,
            sticky=tk.N+tk.S+tk.E+tk.W
        )
        self.twoLabelVar.set('2')

        self.threeLabel = tk.Label(
            self.root,
            font=self.font,
            relief=tk.SUNKEN,
            textvariable=self.threeLabelVar
        )
        self.threeLabel.grid(
            row=0,
            column=2,
            sticky=tk.N+tk.S+tk.E+tk.W
        )
        self.threeLabelVar.set('3')

        self.fourLabel = tk.Label(
            self.root,
            font=self.font,
            relief=tk.SUNKEN,
            textvariable=self.fourLabelVar
        )
        self.fourLabel.grid(
            row=1,
            column=0,
            sticky=tk.N+tk.S+tk.E+tk.W
        )
        self.fourLabelVar.set('4')

        self.fiveLabel = tk.Label(
            self.root,
            font=self.font,
            relief=tk.SUNKEN,
            textvariable=self.fiveLabelVar
        )
        self.fiveLabel.grid(
            row=1,
            column=1,
            sticky=tk.N+tk.S+tk.E+tk.W
        )
        self.fiveLabelVar.set('5')

        self.sixLabel = tk.Label(
            self.root,
            font=self.font,
            relief=tk.SUNKEN,
            textvariable=self.sixLabelVar
        )
        self.sixLabel.grid(
            row=1,
            column=2,
            sticky=tk.N+tk.S+tk.E+tk.W
        )
        self.sixLabelVar.set('6')
        
        def startInterface(self):
    
        while not self.interface:
    
            try:
                ser = obd.serialport.SerialPort(serialPort)
                self.interface = obd.interface.elm.create(ser)
                self.interface.open()
                self.interface.set_protocol(None)
        
                while not self.interface.connected_to_vehicle:
    
                    try:
                        self.interface.connect_to_vehicle()
                    except obd.exception.ConnectionError as ce:
                        print(str(ce))
                        self.interface._flush_frames()
                    except obd.exception.CommandNotSupported as cns:
                        print(str(cns))
                        self.interface.close()
                        self.interface.port.port.close()
                        self.interface = None
                    except obd.exception.ReadTimeout as rt:
                        print(str(rt))
                        self.interface._flush_frames()
                    except obd.exception.InterfaceError as ie:
                        print(str(ie))
                        self.interface._flush_frames()
    
            except obd.exception.OBDException as oe:
                print(str(oe))
                self.interface = None
                time.sleep(1)
            except obd.exception.ReadTimeout as rt:
                print(str(rt))
                self.interface.close()
                self.interface.port.port.close()
                self.interface = None
                time.sleep(1)
            except obd.exception.InterfaceError as ie:
                print(str(ie))
                self.interface.close()
                self.interface.port.port.close()
                self.interface = None
                time.sleep(1)
            except AttributeError as ae:
                print(str(ae))
                self.interface = None

        def displayOBDGauges(self):

                while True:

                        try:
                                request = obd.message.OBDRequest(sid=0x01, pid=0x05)

                                responses = self.interface.send_request(request)
                                self.oneLabelVar.set(str((responses[0].values[0].value * 1.8) + 32.0).ljust(5, '0')[:5] + '\ndeg F')

                                request = obd.message.OBDRequest(sid=0x01, pid=0x0c)
                                responses = self.interface.send_request(request)
                                self.twoLabelVar.set(str(int(responses[0].values[0].value)) + '\nRPM')

                                request = obd.message.OBDRequest(sid=0x01, pid=0x10)
                                responses = self.interface.send_request(request)
                                self.threeLabelVar.set(str(responses[0].values[0].value * 0.0805).ljust(5, '0')[:5] + '\nGPH')

                                request = obd.message.OBDRequest(sid=0x01, pid=0x0d)
                                responses = self.interface.send_request(request)
                                velocity_kph = responses[0].values[0].value
                                request = obd.message.OBDRequest(sid=0x01, pid=0x10)
                                responses = self.interface.send_request(request)
                                mass_af_gps = responses[0].values[0].value
                                instant_mpg = velocity_kph * 7.718 / mass_af_gps
                                mpg_total = (self.average_mpg * self.mpg_counter) + instant_mpg
                                self.mpg_counter += 1
                                self.average_mpg = mpg_total / self.mpg_counter
                                self.fourLabelVar.set(str(self.average_mpg).ljust(6, '0')[:6] + '\nMPGc')

                                request = obd.message.OBDRequest(sid=0x01, pid=0x42)
                                responses = self.interface.send_request(request)
                                self.fiveLabelVar.set(str(responses[0].values[0].value).ljust(5, '0')[:5] + '\nV')

                                self.sixLabelVar.set(str(velocity_kph * 0.621371).ljust(5, '0')[:5] + '\nMPH')
                                
                        except obd.exception.IntervalTimeout as ite:
                                print(ite)
                self.interface.close()
                self.interface.port.port.close()
                self.interface = None
                self.startInterface()
                        except obd.exception.ProtocolError as pe:
                                print(pe)
                                self.interface._flush_frames()
                                time.sleep(1)
                        except obd.exception.DataError as de:
                                print(de)
                                self.interface._flush_frames()
                        except NameError as ne:
                                print(ne)
                                self.interface._flush_frames()
                        except ValueError as ve:
                                print(ve)
                                self.interface._flush_frames()
            except IndexError as ie:
                print(ie)
                self.interface._flush_frames()
                        except AttributeError as ae:
                                print(ae)
                                self.interface._flush_frames()
            except AssertionError as ae:
                print(ae)
                self.interface.close()
                self.interface.port.port.close()
                self.interface = None
                                self.startInterface()

                        self.root.update_idletasks()
                        self.root.update()


if __name__ == '__main__':
    app = Application()
    app.master.title('PyOBD Gauges')
    app.displayOBDGauges()
    app.mainloop()
