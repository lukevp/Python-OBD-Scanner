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
This submodule specifies the library-specific exceptions that may
be raised.  The ones most often seen/used are:

OBDException -- the base class for all library-specific exceptions
InterfaceError -- most often appears when there are problems
    communicating with the interface (scan tool)
ConnectionError -- the exception raised when unable to connect
    to the the vehicle; most often this means the key isn't in
    the ignition or the engine is of
DataError -- most often indicates the request isn't supported

ResetRequiresConfirmation -- raised the first time a reset request
    is attempted (to prevent inadvertent reset due to programmer
    error)
"""

import random

from obd.util import debug, untested

class OBDException(Exception):
    """Base class for all library-specific exceptions"""
    def __init__(self, message, raw=None):
        if raw:
            message = "%s (%s)" % (message, repr(raw))
        Exception.__init__(self, message)
        debug("%s: %s" % (type(self), message))
        return

# ----

class InterfaceBusy(OBDException):
    """The previous interface command was interrupted"""
    def __init__(self, message="Interface was processing previous command", response=None):
        untested("interface busy exception")
        OBDException.__init__(self, message)
        self.response = response
        return

# ----

class Timeout(OBDException):
    """Base class for timeout exceptions"""
    def __init__(self, message="Timeout", response=None):
        OBDException.__init__(self, message)
        self.response = response
        debug("response=%r" % response)
        return
    
class IntervalTimeout(Timeout):
    """Raised by read routines if a polling interval passes without data"""
    def __init__(self, message="Partial response", response=None):
        Timeout.__init__(self, message, response)
        return

class ReadTimeout(Timeout):
    """Raised by read_until_* routines if they time out"""
    def __init__(self, message="Incomplete response", response=None):
        Timeout.__init__(self, message, response)
        return

# ----
    
class InterfaceError(OBDException):
    """Errors between the computer and OBD interface, generally OK to retry"""
    def __init__(self, message="Error communicating with OBD interface", raw=None):
        OBDException.__init__(self, message, raw)
        return

class CommandNotSupported(InterfaceError):
    """A command sent to the interface was not understood"""
    pass

class InterfaceNotFound(InterfaceError):
    """Unable to find any interfaces via enumeration"""
    pass

# ----

class ResetRequiresConfirmation(OBDException):
    """A reset request was attempted without a confirmation token
    
    This exception is expected the first time a reset request is attempted by
    an interface.  The reset should then be retried with the randomly-generated
    token provided by this exception."""
    def __init__(self, message="Reset requests require a confirmation token"):
        token = random.randint(0, 0xFFFFFFFF)
        OBDException.__init__(self, message, raw=token)
        self.token = token
        return

# ----

class VehicleException(OBDException):
    """Unexpected events between the OBD interface and vehicle"""
    def __init__(self, message="Error communicating with vehicle", raw=None):
        OBDException.__init__(self, message, raw)
        return

class DataError(VehicleException):
    """Generally transient data errors in communicating with vehicle"""
    pass

class BufferOverflowError(DataError):
    """Vehicle is transmitting data faster than the interface can send it
    to the computer
    """
    pass

class ConnectionError(VehicleException):
    """Unable to establish a connection with the vehicle; it may not be on"""
    pass

class BusError(VehicleException):
    """Errors on the OBD bus that are usually caused by wiring problems,
    generally permanent
    """
    def __init__(self, message):
        untested("bus error exception")
        VehicleException.__init__(self, "Probable wiring error: %s" % message)
        return

class ProtocolError(VehicleException):
    """Errors on the OBD bus that are usually caused by configuration
    problems, may retry
    """
    pass

class J1699Failure(VehicleException):
    """OBD responses that fail J1699 conformance tests"""
    pass
    
# vim: softtabstop=4 shiftwidth=4 expandtab                                     
