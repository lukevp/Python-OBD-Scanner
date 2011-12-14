#!/usr/bin/env python -3
########################################################################
# pyOBD-II -- a Python library for communicating with OBD-II vehicles
# Copyright (C) 2009 Peter J. Creath
#
# This file is part of pyOBD-II ("pyobd2").
#
# You can redistribute pyOBD-II and/or modify it under the terms of
# the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option)
# any later version.
#
# To negotiate alternative licensing terms, please contact the author.
# See the LICENSE.txt file at the top of the source tree for further
# information.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyOBD-II.  If not, see <http://www.gnu.org/licenses/>.
########################################################################

"""High-level serial port support for Interfaces.  Provides enumeration
of serial ports and port recording/playback for regression testing.
"""

import sys
import glob
import time
try:
    import serial as pyserial
except ModuleError:
    sys.stderr.write("pyserial is needed")
    sys.exit()

import obd.exception as exception
from obd.util import warn, error

class SerialPort(object):
    """Class used by Interfaces for managing common serial-port related tasks
    """
    ports = []

    def enumerate():
        """Return a list of available serial ports.
        
        The serial ports are represented as the port name or ID to be
        pass to the SerialPort initializer."""
        ports = SerialPort.ports
        if (len(ports) > 0):
            return ports

        if (sys.platform.startswith("darwin")):
            ports = SerialPort._find_mac_serial_ports()
        else:
            raise OBDException("Automatic interface detection not implemented for " + sys.platform)
        SerialPort.ports = ports
        return SerialPort.ports
    enumerate = staticmethod(enumerate)

    def _find_mac_serial_ports():
        """Return the list of Mac serial (not USB) ports"""
        ports = []
        for name in glob.glob("/dev/cu.*"):
            try:
                f = open(name, "rw")
                f.close()
                ports.append(name)
            except:
                pass

        return ports
    _find_mac_serial_ports = staticmethod(_find_mac_serial_ports)

    def __init__(self, port):
        """
        port -- the serial port name or ID needed for pyserial
            to open the port; e.g., /dev/cu.1234, COM1, etc.
        """
        self.port = pyserial.Serial(port,
                                    baudrate = 38400,
                                    parity = pyserial.PARITY_NONE,
                                    stopbits = pyserial.STOPBITS_ONE,
                                    bytesize = pyserial.EIGHTBITS,
                                    timeout = 2)
        self.name = port
        self.interval = 2

    def write(self, str):
        """Write the given string to the port"""
        self.port.flushOutput()
        self.port.flushInput()
        self.port.write(str)
        return

    MAX_READ_OVERRUN = 0.01
    def read_until_string(self, str):
        """Read from the port until the given string is detected
        or the read times out, whichever comes first.
        
        str -- the string to await
        
        Raises an IntervalTimeout exception if the polling interval
        expires without receiving any data.  Raises a ReadTimeout
        exception if the read timout expires before the given string
        is encountered.  See set_timeout for more details.
        """
        buffer = ""
        interval = self.interval
        try:
            while True:
                remaining = self.timeout - time.time()
                if (remaining <= 0):
                    raise exception.ReadTimeout(response=buffer)
                # make sure the read() doesn't go beyond the timeout
                if remaining < interval and interval >= self.MAX_READ_OVERRUN:
                    interval = remaining / 2.0
                    self.port.setTimeout(interval)
                # read() times out after the polling interval set by set_timeout()
                c = self.port.read(1)
                if len(c) == 0 and interval == self.interval:
                    # stop if the read timed out without data
                    raise exception.IntervalTimeout(response=buffer)
                # FIXME: move 0x00 test to ELM327
                if c == '\x00': continue  # per note on p.6 of ELM327 data sheet
                buffer += c
                if (buffer.endswith(str)):
                    break
        finally:
            # if we temporarily dialed down the port's timeout to avoid
            # galloping past the timeout, restore it to its previous value
            if interval != self.interval:
                self.port.setTimeout(self.interval)

        return buffer

    def get_baudrate(self):
        """Return the currently configured baud rate."""
        return self.port.getBaudrate()

    def set_baudrate(self, baud):
        """Set the serial port baud rate."""
        self.port.setBaudrate(baud)
        return
    
    def set_timeout(self, timeout, interval=None):
        """Set the timeout and polling interval for read operations.
        
        timeout -- the maximum time to spend before raising a timeout
            exception (plus at most MAX_READ_OVERRUN seconds)
        interval -- the polling interval; the maximum time to wait
            without receiving any data
        """
        self.timeout = time.time() + timeout
        if interval == None:
            interval = timeout
        if interval != self.interval:
            self.interval = interval
            # requires reconfiguring the port on some platforms, so avoid unnecessary calls
            self.port.setTimeout(interval)
        return
    
    def clear_rx_buffer(self):
        """Clear the receive buffer"""
        self.port.flushInput()
        return
    
    def clear_tx_buffer(self):
        """Clear the transmission buffer"""
        self.port.flushOutput()
        return


class SerialPortRecorder(SerialPort):
    """A SerialPort variant which records all activity to a file for
    subsequent review or playback.  See SerialPortPlayback as well.
    """
    def __init__(self, port, filename):
        """port -- the serial port name or ID needed for pyserial
            to open the port; e.g., /dev/cu.1234, COM1, etc.
        filename -- the file to which to record serial port activity
        """
        SerialPort.__init__(self, port)
        self.logfile = file(filename, "w")
        self.logfile.write("%s\n" % port)
        self.start_time = time.time()
        return

    def log(self, str):
        """Write the given string to the log file along with a timestamp"""
        self.logfile.write("%0.4f %s\n" % (time.time() - self.start_time, str))
        return
        
    def write(self, str):
        """Write (and log) the given string to the port"""
        self.log("write %r" % str)
        SerialPort.write(self, str)
        return
    
    def read_until_string(self, string):
        """Read from the port until the given string is detected
        or the read times out, whichever comes first, and log the
        result.  See SerialPort.read_until_string() for details.
        """
        try:
            result = SerialPort.read_until_string(self, string)
            self.log("read-until %r = %r" % (string, result))
        except exception.Timeout as e:
            if isinstance(e, exception.IntervalTimeout): status = "interval-expired"
            else: status = "timeout-expired"
            result = e.response
            self.log("read-until %r = %r [%s]" % (string, result, status))
            raise e
        return result
    
    def set_baudrate(self, baud):
        """Set (and log) the serial port baud rate"""
        SerialPort.set_baudrate(self, baud)
        self.log("set-baud %d" % baud)
        return
    
    def set_timeout(self, timeout, interval=None):
        """Set (and log) the timeout and polling interval for read
        operations.  See SerialPort.set_timeout() for details.
        """
        SerialPort.set_timeout(self, timeout, interval)
        self.log("set-timeout %f %f" % (timeout, self.interval))
        return

    def clear_rx_buffer(self):
        """Clear the receive buffer"""
        SerialPort.clear_rx_buffer(self)
        self.log("clear rx")
        return
    
    def clear_tx_buffer(self):
        """Clear the transmission buffer"""
        SerialPort.clear_tx_buffer(self)
        self.log("clear tx")
        return


class SerialPortPlayback(SerialPort):
    """A SerialPort variant which replays activity previously recorded
    to a file.  See SerialPortRecorder as well.
    
    In practice, this playback expects to see the same calls with the
    same arguments in the same order as in the recording session.
    Minor differences, such as timeout values or baud rates, emit
    a warning but can otherwise be ignored.  Other differences raise
    ValueErrors.
    
    As a result, this is useful mostly for automated regression testing
    and debugging specific test cases.
    """
    def __init__(self, filename, mimic_timing=False):
        """filename -- the file containing serial port activity to replay
        mimic_timing -- True to cause calls to methods to take as
            long to return as they did during the recording session;
            otherwise they return immediately.
        """
        try:
            SerialPort.__init__(self, None)
        except:
            pass
        self.logfile = file(filename, "r")
        port = self.logfile.readline().rstrip('\r\n')
        self.name = "[Playback of %s from %s]" % (port, filename)
        self.mimic_timing = mimic_timing
        self.baudrate = 38400
        self.timestamp = None
        self.line_number = 1
        return

    def next_log(self, expected_action):
        """Return the next line from the log file and raise an exception
        if there's a major discrepancy.
        """
        line = self.logfile.readline()
        if not line: raise EOFError()
        self.line_number += 1
        line = line.rstrip('\r\n')
        timestamp, log_action, parameters = line.split(" ", 2)
        timestamp = float(timestamp)
        if not self.timestamp: self.timestamp = timestamp
        if expected_action != log_action:
            error("%d: %s != %s" % (self.line_number, expected_action, log_action))
            raise ValueError
        return timestamp, parameters
        
    def write(self, str):
        """Pretend to write the given string to the port, raising an
        exception if that's not what was written in the recorded session.
        """
        timestamp, log_str = self.next_log("write")
        log_str = eval(log_str)
        if str != log_str:
            error("%d: write(%r) != log(%r)" % (self.line_number, str, log_str))
            raise ValueError
        self.timestamp = timestamp
        return
    
    def read_until_string(self, str):
        """Pretend to read from the port until the given string is
        detected or the read times out.  Return the previously recorded
        result.
        """
        timestamp, parameters = self.next_log("read-until")
        # extract the argument, result, and status
        status = None
        if parameters.endswith("]"):
            pos = parameters.rindex(" [")
            status = parameters[pos+2:-1]
            parameters = parameters[:pos]
        log_str, log_result = [eval(p) for p in parameters.split(" = ", 1)]

        if log_str != str:
            warn("%d: read-until(%r) != log(%r)" % (self.line_number, str, log_str))

        if self.mimic_timing:
            time.sleep(timestamp - self.timestamp)

        self.timestamp = timestamp
        if status == "interval-expired":
            raise exception.IntervalTimeout(response=log_result)
        if status == "timeout-expired":
            raise exception.ReadTimeout(response=log_result)
        return log_result
    
    def get_baudrate(self):
        """Return the currently configured baud rate"""
        return self.baudrate
    
    def set_baudrate(self, baud):
        """Pretend to set the serial port baud rate"""
        timestamp, baudrate = self.next_log("set-baud")
        baudrate = int(baudrate)
        if baudrate != baud:
            warn("%d: set-baud(%d) != %d" % (self.line_number, baud, baudrate))
        self.baudrate = baudrate
        self.timestamp = timestamp
        return
    
    def set_timeout(self, timeout, interval=None):
        """Pretend to set the timeout and polling interval"""
        if interval == None: interval = timeout
        timestamp, parameters = self.next_log("set-timeout")
        log_timeout, log_interval = [float(p) for p in parameters.split(" ")]
        if timeout != log_timeout or interval != log_interval:
            warn("%d: set-timeout(%f,%f) != log(%f,%f)" %
                  (self.line_number, timeout, interval, log_timeout, log_interval))
        self.timestamp = timestamp
        return

    def clear_rx_buffer(self):
        """Pretend to clear the receive buffer"""
        timestamp, buffer = self.next_log("clear")
        if buffer != "rx":
            warn("%d: clear %s != rx" % (self.line_number, buffer))
        return
    
    def clear_tx_buffer(self):
        """Pretend to clear the transmission buffer"""
        timestamp, buffer = self.next_log("clear")
        if buffer != "tx":
            warn("%d: clear %s != tx" % (self.line_number, buffer))
        return

# vim: softtabstop=4 shiftwidth=4 expandtab                                     
