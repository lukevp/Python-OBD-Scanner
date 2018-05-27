#!/usr/bin/python

import PyOBD2

if __name__ == "__main__":

    pyobd2 = PyOBD2.PyOBD2()
    pyobd2.startInterface()

    while True:
        data = pyobd2.runMonitor()
        if data:
            msg_string = (
                str(
                    data['engine_coolant_temp_degF']
                ).ljust(5, '0')[:5] + 
                ' deg F; ' +
                str(
                    data['engine_consumption_gph']
                ).ljust(5, '0')[:5] + 
                ' gph; ' +
                str(
                    data['average_mpg']
                ).ljust(6, '0')[:6] +
                ' mpgc; ' +
                str(
                    data['control_module_voltage']
                ).ljust(5, '0')[:5] +
                ' V;'
            )
            print(msg_string)

    pyodb2.shutdown()

