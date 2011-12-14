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

"""
Support for ELM32X-compatible interfaces

Basic usage:

    enumerate() -- return a list of attached ELM32x OBD-II interfaces,
        each of which is an instance of the appropriate ELM32X subclass

    create(port) -- create an instance of the appropriate ELM32X
        subclass at the given port

Note that in the usual case, this is handled completely via
obd.interface.enumerate(), which calls the appropriate enumeration
and creation methods for registered classes.

Alternatively, clients can call obd.interface.create(identifier),
which similarly calls the appropriate creation method for the
interface specified by the given identifier.
"""

import re
import time
import copy
import serial.serialutil

import obd.serialport
import obd.exception
import obd.message
import obd.protocol
from obd.util import debug, unimplemented, untested
from obd.interface import register_interface_class
from obd.exception import InterfaceError
from obd.interface.base import Interface


def enumerate(callback=None):
    """Return a list of attached ELM32x OBD-II interfaces, each
    of which is an instance of the appropriate ELM32X subclass.
    
    callback -- the callback function to pass to the initializer
    """
    interfaces = []
    ports = obd.serialport.SerialPort.enumerate()
    for port in ports:
        try:
            serialport = obd.serialport.SerialPort(port)
            baud = ELM32X.detect_baudrate(serialport)
            if baud:
                interface = create(serialport, callback, baud)
                interfaces.append(interface)
        except serial.serialutil.SerialException as e:
            raise InterfaceError(str(e))
        except InterfaceError as e:
            pass
        except Exception as e:
            debug(e)
    return interfaces


_classes = {}
def create(port, callback=None, baud=None):
    """Create an instance of the appropriate ELM32X subclass at the
    given port
    
    port -- the SerialPort subclass to which the interface is attached
    callback -- the callback function used to provide status updates
        (default None)
    baud -- the baud rate to use, or None (default) to auto-detect
    """
    # Use the appropriate baud rate, auto-detecting if requested
    if baud:
        if port.get_baudrate() != baud:
            untested("specifying the baud rate for obd.interface.elm.create()")
            port.set_baudrate(baud)
    else:
        current_baud = ELM32X.detect_baudrate(port)
        if not current_baud:
            raise InterfaceError("Unable to connect to ELM; does it have power?")
    # Query the interface for its identity
    identifier = ELM32X._at_cmd(port, "ATI")
    if identifier.startswith("ATI\r"): identifier = identifier[4:]
    debug(identifier)
    chip_identifier, chip_version = identifier.split(" ")

    # Check for extended command set
    extended = ELM32X._at_cmd(port, "STI")
    if extended.startswith("STI\r"): extended = extended[4:]
    if extended != "?":
        untested(extended)
        chip_identifier, chip_version = extended.rsplit(" ", 1)

    # Create an instance of the appropriate ELM32X subclass
    try:
        elm_class = _classes[chip_identifier]
    except KeyError as e:
        untested("unknown ELM response to ATI")
        raise InterfaceError("Unknown response to ATI: %r" % identifier)
    interface = elm_class(port, chip_identifier, callback=callback)

    debug("%s detected on port %s at %d baud" %
          (chip_identifier, interface.port.name, interface.port.get_baudrate()))
    return interface
    


class ELM32X(Interface):
    """Class representing an ELM32x OBD-II interface.
    
    See obd.interface.base.Interface for usage.
    """

    ATZ_TIMEOUT = 1.5
    AT_TIMEOUT  = 0.13
    PROMPT = ">"

    def __init__(self, port, name=None, callback=None):
        """
        port -- a SerialPort instance corresponding to the port to which
            the ELM device is attached
        name -- the descriptive name of the interface
        callback -- a function to be called with status updates during
            long operations (such as connecting to a vehicle); the one
            argument sent to the callback is a string containing a status
            message
        
        The callback may also be set (or changed) later, via
        set_status_callback().
        """
        assert type(self) != ELM32X, "ELM32X should only be instantiated via obd.interface.elm.create()"
        assert isinstance(port, obd.serialport.SerialPort)
        if name is None:
            untested()
            name = "%s compatible" % self.__class__.__name__
        Interface.__init__(self, port.name, name, callback)
        self.port = port
        self.interface_configured = False
        self.connected_to_vehicle = False
        return

    def enumerate(callback=None):
        """Return a list of attached ELM32x OBD-II interfaces, each
        of which is an instance of the appropriate ELM32X subclass.
        
        callback -- the callback function to pass to the initializer
        """
        return obd.interface.elm.enumerate(callback)
    enumerate = staticmethod(enumerate)

    def create(identifier, callback=None):
        """Create an instance of the appropriate ELM32X subclass at the
        given port

        identifier -- the name of the serial port to which the interface
            is attached
        callback -- the callback function used to provide status updates
            (default None)
        """
        serialport = obd.serialport.SerialPort(identifier)
        interface = create(serialport, callback)
        return interface
    create = staticmethod(create)

    def detect_baudrate(port, timeout=0.03):
        """Detect, select, and return the baud rate at which a connected
        ELM32x interface is operating.

        Return None if the baud rate couldn't be determined.
        """
        # 38400, 9600 are the possible boot bauds (unless reprogrammed via
        # PP 0C).  19200, 38400, 57600, 115200, 230400, 500000 are listed on
        # p.46 of the ELM327 datasheet.
        #
        # Once pyserial supports non-standard baud rates on platforms other
        # than Linux, we'll add 500K to this list.
        #
        # We check the two default baud rates first, then go fastest to
        # slowest, on the theory that anyone who's using a slow baud rate is
        # going to be less picky about the time required to detect it.
        bauds = [ 38400, 9600, 230400, 115200, 57600, 19200 ]

        for baud in bauds:
            port.set_baudrate(baud)
            port.clear_rx_buffer()
            port.clear_tx_buffer()

            # Send a nonsense command to get a prompt back from the scanner
            # (an empty command runs the risk of repeating a dangerous command)
            # The first character might get eaten if the interface was busy,
            # so write a second one (again so that the lone CR doesn't repeat
            # the previous command)
            port.write("\x7F\x7F\r")
            port.set_timeout(timeout)
            try:
                response = port.read_until_string(ELM32X.PROMPT)
            except obd.exception.Timeout:
                continue

            if (response.endswith("\r\r>")):
                #print "%d baud detected (%r)" % (baud, response)
                break
                
        else:
            baud = None

        return baud
    detect_baudrate = staticmethod(detect_baudrate)

    def open(self):
        """Configure the interface (scan tool) for use.
        
        This does not initiate a connection with the vehicle; it simply
        opens the connection between the computer and the interface.
        See connect_to_vehicle() for comparison.
        """
        if self.interface_configured: return

        self.interface_configured = True  # set initially to keep at_cmd from barking
        complete = False
        try:
            self.reset()
            self.at_cmd("ATE0")
            self.at_cmd("ATL0")
            self.at_cmd("ATH1")
            complete = True
        finally:
            # set to its true state before raising any exceptions up the chain
            self.interface_configured = complete

        return

    def reset(self, quick=True):
        """Reset the interface (scan tool)
        
        quick -- peform a quick reset (if supported), otherwise perform
            a slower, full reset
        """
        if quick:
            self.at_cmd("ATWS")
        else:
            # Since the baud rate might change after the ATZ, we just wait
            # and clear the receive buffer.
            self._write("ATZ\r")
            time.sleep(ELM32X.ATZ_TIMEOUT)
            self.port.clear_rx_buffer()  # ignore any garbage due to wrong baud rate
            debug("baud on reset = %s" % ELM32X.detect_baudrate(self.port))
        return

    def close(self):
        """Release the interface (scan tool) from use.  This may
        or may not disconnect the communication session between
        the interface and the vehicle, depending on implementation.
        """
        if not self.interface_configured: return

        self.reset(quick=False)
        return

    def _at_cmd(port, cmd, timeout=None):
        """(Static) Send a command to the port and return the response.
        
        This is a private class method to allow non-instance methods
        (such as create()) to read an ELM response.  The publicly
        exposed version of this is an instance method.
        """
        port.write("%s\r" % cmd)
        if timeout is None: timeout = ELM32X.AT_TIMEOUT
        port.set_timeout(timeout)
        response = ELM32X._static_read_until_prompt(port)
        return response
    _at_cmd = staticmethod(_at_cmd)
    
    def at_cmd(self, cmd, timeout=None):
        """Send a command to the interface and return the response.
        
        cmd -- the command to send
        timeout -- the maximum time to wait for a response, or None
            (the default) to use ELM32X.AT_TIMEOUT"""
        assert self.interface_configured
        return ELM32X._at_cmd(self.port, cmd, timeout)

    def _send_obd_message(self, message, header=None, token=None):
        """Transmit an OBD message on the bus.
        
        message -- the message bytes to transmit
        header -- the header used to address the message (or None
            for broadcast)
        token -- the token required to send a Reset message
            (if applicable)
        """
        assert self.interface_configured
        assert self.connected_to_vehicle
        if header:
            unimplemented("ELM support for explicitly addressed requests")

        # Before letting a reset command out to the interface, make sure
        # it's intentional (raising an exception if not)
        if message[0] == 0x04:
            self._verify_token(token)
        message = " ".join(["%02X" % b for b in message])
        self._write("%s\r" % message)

        self._set_timeout(Interface.OBD_REQUEST_TIMEOUT, 3.0)
        response = self._read_response()
        return self._message_bytes_from_ascii(response)

    def _message_bytes_from_ascii(self, ascii_messages):
        """Convert each ASCII message into a list of raw bytes
        and return the list of raw messages.
        """
        raw_messages = []
        debug(ascii_messages)
        for message in ascii_messages:
            message = message.replace(" ", "")
            # pad 11-bit CAN headers out to 32 bits for consistency,
            # since ELM already does this for 29-bit CAN headers
            if len(message) & 1: message = "00000" + message
            raw_message = []
            for i in range(0, len(message), 2):
                raw_message.append(int(message[i:i+2], 16))
            raw_messages.append(raw_message)
        debug(raw_messages)
        return raw_messages

    def _write(self, str):
        """Write the given string to the interface's port"""
        return self.port.write(str)

    def _read_until_string(self, str):
        """Read from the interface's port until the given string is
        detected or the read times out, whichever comes first.
        
        str -- the string to await
        
        Raises an IntervalTimeout exception if the polling interval
        expires without receiving any data.  Raises a ReadTimeout
        exception if the read timout expires before the given string
        is encountered.  See _set_timeout for more details.
        """
        result = self.port.read_until_string(str)
        if result.startswith("STOPPED"):
            raise InterfaceBusy(result)
        return result
    
    def _static_read_until_prompt(port):
        """(Static) Read from the port until the prompt is received
        and return the response.
        
        This is a private class method to allow non-instance methods
        (such as create()) to read an ELM response.  The publicly
        exposed version of this is an instance method.
        """
        response = port.read_until_string(ELM32X.PROMPT)
        # remove trailing prompt string
        if response.endswith(ELM32X.PROMPT):
            response = response[:-len(ELM32X.PROMPT)]
        # remove superfluous EOLs surrounding actual response
        response = response.strip("\r")
        # raise an exception if we interrupted an operation
        if response.startswith("STOPPED"):
            raise InterfaceBusy(response)
        return response
    _static_read_until_prompt = staticmethod(_static_read_until_prompt)

    def _read_until_prompt(self):
        """Read from the interface until the prompt is received
        and return the response.
        """
        return ELM32X._static_read_until_prompt(self.port)

    def _set_timeout(self, timeout, interval=None):
        """Set the timeout and polling interval for read operations.
        
        timeout -- the maximum time to spend before raising a timeout
            exception
        interval -- the polling interval; the maximum time to wait
            without receiving any data
        """
        return self.port.set_timeout(timeout, interval)

    def connect_to_vehicle(self):
        """Initiate a communication session with the vehicle's ECU
        and return the session protocol.

        This may take several seconds, particularly if automatic protocol
        detection is being used.  Where possible, the specified callback
        function will be used to provide status updates.
        
        Raises an exception if unable to establish the connection.

        On an ELM32x interface, this sends an initial OBD command to
        initiate the connection.
        """
        self._current_status = ""
        self.open()
        if self.connected_to_vehicle:
            raise CommandNotSupported("Already connected to vehicle")
        self._protocol_response = None
        
        self._status_callback("Connecting to vehicle...")
        self._write("0100\r")  # must be supported by all OBD-II vehicles
        self._set_timeout(Interface.OBD_REQUEST_TIMEOUT)

        # Read a complete line, allowing for incremental status updates
        line = ""
        status_line = False
        while not line.endswith("\r"):
            try:
                line += self._read_until_string("")
            except obd.exception.ReadTimeout as e:
                raise InterfaceError(raw=line+e.response)

            if not status_line:
                if line.startswith("SEARCHING..."):
                    status_line = True
                    self._status_callback("Searching for protocol...")
                elif line.startswith("BUS INIT: "):
                    status_line = True
                    self._status_callback("Initializing bus...")

            if status_line and line == "SEARCHING...\r":
                # The subsequent line will either be the error message
                # or the OBD response, so eat this line and keep going.
                status_line = False
                line = ""
            continue

        # Handle connection failures
        line = line[:-1] # strip \r
        try:
            if line.startswith("STOPPED"):
                raise obd.exception.InterfaceBusy(line)
            if line.endswith("UNABLE TO CONNECT") or line.endswith("ERROR"):
                raise obd.exception.ConnectionError(raw=line)
            if line.startswith("BUS INIT: ") and not line.endswith("OK"):
                raise obd.exception.ConnectionError(raw=line)
            if line == "NO DATA":
                raise obd.exception.ConnectionError(raw=line) # probably not SAE J1850
        except obd.exception.OBDException as e:
            self._read_until_prompt() # swallow the rest of the response
            raise e
        line += "\r" # re-add \r
    
        # Read the actual OBD response
        if status_line: line = ""  # swallow any status line
        lines = self._read_response(previous_data=line)
        debug("result: " + str(lines))

        # Determine and verify the protocol established
        self.connected_to_vehicle = True
        self.vehicle_protocol = self.get_protocol()

        # Process the response to make sure we got valid data
        raw_frames = self._message_bytes_from_ascii(lines)
        self._process_obd_response(raw_frames)

        # Return the actual protocol established
        return self.vehicle_protocol
    
    def disconnect_from_vehicle(self):
        """Terminate an existing communication session with a
        vehicle.
        
        Raises an exception if there is no active session.
        """
        if not self.connected_to_vehicle:
            raise CommandNotSupported("Already disconnected from vehicle")
        self.at_cmd("ATPC")
        self.connected_to_vehicle = False
        return
        
    def _read_response(self, previous_data=""):
        """Read ASCII OBD frames from the interface until the
        prompt is received, and return the list of frames.
        
        Raises an exception on any error (such as no data,
        buffer overflow, etc.)
        
        previous_data -- data previously read from the interface
            which should be considered part of the response
        """
        response = previous_data + self._read_until_prompt()
        response = response.strip("\r")
        lines = response.split("\r")
        for line in lines:
            # Raise exceptions for any errors
            if line == "?":
                raise CommandNotSupported()

            if line == "NO DATA":
                raise obd.exception.DataError(raw=line)            
            if line.endswith("BUS BUSY") or line.endswith("DATA ERROR"):
                untested("data error")
                raise obd.exception.DataError(raw=line)
            if line.endswith("BUS ERROR") or line.endswith("FB ERROR") or line.endswith("LV RESET"):
                untested("bus error")
                raise obd.exception.BusError(raw=line)
            if line.endswith("CAN ERROR") or line.endswith("RX ERROR"):
                untested("protocol error")
                raise obd.exception.ProtocolError(raw=line)
            if line.endswith("BUFFER FULL"):
                untested("buffer overflow")
                raise BufferOverflowError()

            if line.find("<DATA ERROR") != -1:
                untested("frame data error")
                # Once we have a test case, we should probably simply replace
                # lines with bad bytes with "None" for each byte; then
                # process_obd_response or send_request will raise the error.
                raise obd.exception.DataError(raw=line)

            matched = re.search(r"ERR\d\d", line)
            if (matched):
                untested("internal ELM error")  # or does this only occur on connection?
                error = matched.group(0)
                if error == "ERR94":
                    # ERR94 is a fatal CAN error according to p.52-53 of the ELM327 datasheet
                    raise obd.exception.BusError(raw=line)
                raise ELM32XError(error)

        return lines

register_interface_class(ELM32X)


class ELM327(ELM32X):
    """Class representing an ELM327 OBD-II interface.
    
    See obd.interface.base.Interface for usage.
    """
    _supported_protocols = {
        "0": None,  # ELM327 automatic search; fast, but doesn't work on all vehicles
        "1": obd.protocol.PWM(),
        "2": obd.protocol.VPW(),
        "3": obd.protocol.ISO9141_2(),
        "4": obd.protocol.ISO14230_4("5BAUD"),
        "5": obd.protocol.ISO14230_4("FAST"),
        "6": obd.protocol.ISO15765_4(id_length=11, baud=500000),
        "7": obd.protocol.ISO15765_4(id_length=29, baud=500000),
        "8": obd.protocol.ISO15765_4(id_length=11, baud=250000),
        "9": obd.protocol.ISO15765_4(id_length=29, baud=250000),
        "A": obd.protocol.SAE_J1939(id_length=29, baud=250000)
        }

    def __init__(self, port, name=None, callback=None):
        """
        port -- a SerialPort instance corresponding to the port to which
            the ELM device is attached
        name -- the descriptive name of the interface
        callback -- a function to be called with status updates during
            long operations (such as connecting to a vehicle); the one
            argument sent to the callback is a string containing a status
            message
        
        The callback may also be set (or changed) later, via
        set_status_callback().
        """
        ELM32X.__init__(self, port, name, callback=callback)
        return

    def get_supported_protocols(self):
        """Return the list of supported protocols for this interface.
        
        Each item in the list is a copy of a Protocol object (or None).
        """
        return [copy.copy(p) for p in self._supported_protocols.values()]
    supported_protocols = property(get_supported_protocols,
                                   doc="The list of supported protocols for this interface.")

    def set_protocol(self, protocol):
        """Select the protocol to use for communicating with the vehicle.
        This will disconnect any communication session with the vehicle
        already in progress.
        
        protocol -- the protocol to use, or None for automatic selection
            by the interface
        """
        if self.connected_to_vehicle: self.disconnect_from_vehicle()
        for key, value in self._supported_protocols.items():
            if value == protocol:
                self.at_cmd("ATTP %s" % key)
                break
        else:
            untested("unsupported protocol requested of ELM")
            raise ValueError("Unsupported protocol: %s" % str(protocol))
        return
    
    def get_protocol(self):
        """Return the current protocol being used in communication with the
        vehicle.

        Raises an exception if not connected with a vehicle.
        """
        if not self.connected_to_vehicle:
            raise CommandNotSupported("Not connected to vehicle")
        response = self.at_cmd("ATDPN")
        # suppress any "automatic" prefix
        if len(response) > 1 and response.startswith("A"):
            response = response[1:]
        # get the protocol object identified by the response
        try:
            protocol = self._supported_protocols[response]
        except KeyError as e:
            untested("unknown protocol returned by ELM")
            raise InterfaceError("Unknown protocol %r" % response)
        # bark if the protocol changed out from under us
        if self._protocol_response is None:
            self._protocol_response = response
        else:
            if response != self._protocol_response:
                untested("unexpected change in protocol")
                raise InterfaceError("Protocol changed unexpectedly")
        # return a copy to prevent muddling the internal list
        return copy.copy(protocol)
    
    def set_baudrate(self, new_baud):
        """Change the baud rate between computer and ELM327 interface.

        Raises an exception if unable to change the baud rate as requested.
        """
        self.open()
        old_baud = self.port.get_baudrate()
        succeeded = False

        # Compute the divisor for the requested baud rate
        divisor = round(4000000.0/new_baud, 0)
        if (divisor < 8 or divisor > 255):
            # Limits specified on p.46 of ELM327 datasheet
            raise ValueError("Baud rate %d out of range for ELM" % new_baud)

        # Get the AT I string (which BRD returns to confirm the new baud rate)
        identifier = self.at_cmd("ATI")

        # Send the BRD command
        command = "ATBRD %02X\r" % divisor
        self._write(command)
        self._set_timeout(ELM32X.AT_TIMEOUT)
        try:
            response = self._read_until_string(str="OK\r")
        except Timeout:
            pass

        # Check whether AT BRD is supported
        if (not response.endswith("OK\r")):
            raise CommandNotSupported("Scanner doesn't support AT BRD; " +
                                      "staying at %d" % old_baud)
        try:
            # Set the port to the new baud rate
            self.port.set_baudrate(new_baud)

            # Check whether the test transmission came through OK
            self._set_timeout(0.1)
            try:
                response = self._read_until_string(str="\r")
            except Timeout:
                pass
            if (response != identifier):
                raise InterfaceError("Test of %d baud failed" % new_baud)

            # If test transmission was OK, send a CR to confirm the change...
            self._write("\r")

            # ...and check for the scanner's confirmation
            self._set_timeout(0.1)
            try:
                response = self._read_until_string(str=ELM32X.PROMPT)
            except Timeout:
                pass
            if (not response.endswith("OK\r\r>")):
                raise InterfaceError("Scanner failed to confirm %d baud" %
                                 new_baud)
        except InterfaceError as e:
            self.port.set_baudrate(self, old_baud)
            raise InterfaceError(str(e) + ("; reverted to %d" % old_baud))

        return

_classes["ELM327"] = ELM327


class _ELM320(ELM32X):
    """Class representing an ELM320 OBD-II interface.
    Not yet implemented.
    
    See obd.interface.base.Interface for usage.
    """
    _supported_protocols = [
	# ELM320 supports only PWM
        obd.protocol.PWM(),
        ]
    def __init__(self, port, name=None, callback=None):
        ELM32X.__init__(self, port, name, callback=callback)
        unimplemented("ELM320 support")
        return
_classes["ELM320"] = _ELM320


class _ELM322(ELM32X):
    """Class representing an ELM322 OBD-II interface.
    Not yet implemented.
    
    See obd.interface.base.Interface for usage.
    """
    _supported_protocols = [
	# ELM322 supports only VPW
        obd.protocol.VPW(),
        ]
    def __init__(self, port, name=None, callback=None):
        ELM32X.__init__(self, port, name, callback=callback)
        unimplemented("ELM322 support")
        return
_classes["ELM322"] = _ELM322

class _ELM323(ELM32X):
    """Class representing an ELM323 OBD-II interface.
    Not yet implemented.
    
    See obd.interface.base.Interface for usage.
    """
    _supported_protocols = [
	# ELM323 supports only ISO 9141-2 and ISO14230-4
        obd.protocol.ISO9141_2(),
        obd.protocol.ISO14230_4("5BAUD"),
        obd.protocol.ISO14230_4("FAST"),
        ]
    def __init__(self, port, name=None, callback=None):
        ELM32X.__init__(self, port, name, callback=callback)
        unimplemented("ELM323 support")
        return
_classes["ELM323"] = _ELM323


class ELM32XError(InterfaceError):
    """ELM-specific internal errors"""
    def __init__(self, id):
        untested("ELM-specific exception")
        InterfaceError.__init__(self, message="Internal ELM error; contact interface vendor", raw=id)
        return


class OBDLinkCI(ELM327):
    """Class representing an OBDLink CI (ELM327-compatible)
    OBD-II interface.
    
    See obd.interface.base.Interface for usage.
    """
    _supported_protocols = {
        "0": None,  # OBDLink automatic search
        # VPW and PWM are not supported
        "3": obd.protocol.ISO9141_2(),
        "4": obd.protocol.ISO14230_4("5BAUD"),
        "5": obd.protocol.ISO14230_4("FAST"),
        "6": obd.protocol.ISO15765_4(id_length=11, baud=500000),
        "7": obd.protocol.ISO15765_4(id_length=29, baud=500000),
        "8": obd.protocol.ISO15765_4(id_length=11, baud=250000),
        "9": obd.protocol.ISO15765_4(id_length=29, baud=250000),
        # SAE J1939 is not supported
        }
_classes["OBDLink CI"] = OBDLinkCI

# vim: softtabstop=4 shiftwidth=4 expandtab                                     

