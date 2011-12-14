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

"""Implementation of OBDRequest and RawRequest"""

from obd.util import *

class Request(object):
    """A class for encapsulating requests to send to the OBD bus via
    interface.send_request()
    
    message() -- returns the actual bytes to send to the bus
    """
    def __init__(self):
        return
    def message(self, protocol):
        """Return the actual bytes to send to the bus"""
        raise NotImplementedError()

class RawRequest(Request):
    """A class for passing raw bytes to the bus
    
    Whatever bytes are passed in get passed on to the bus.  This
    allows clients to pass arbitrary data via interface.send_request().
    """
    def __init__(self, data):
        """Create a Request object to send the bytes as given
        
        data -- the bytes to send on on the OBD bus
        """
        if not isinstance(data, list):
            raise ValueError("RawRequest requires a list of bytes")
        Request.__init__(self)
        self.data = data
        return
    def message(self, protocol):
        """Return the actual bytes to send to the bus"""
        return self.data
        
class OBDRequest(Request):
    """A class for sending OBD SID/PID requests to the vehicle
    
    This allows clients to send most (all?) OBD requests given the
    SID and optional PID(s).
    """
    def __init__(self, sid, pid=None):
        """Create a Request object representing an OBD request with
        the given SID and optional PID(s).
        
        sid -- the Service or Mode ID to request
        pid -- the Parameter ID (or equivalent to request); None if the
            given SID does not use PIDs; when supported, this may
            also be a list of PIDs.
        """
        Request.__init__(self)
        self.sid = sid
        if pid is None:
            self.data = []
        elif isinstance(pid, list):
            unimplemented("support for multiple PIDs per request")
            self.data = pid
        else:
            self.data = [pid]
        return
    def message(self, protocol):
        """Return the actual bytes to send to the bus"""
        return [self.sid] + self.data


# vim: softtabstop=4 shiftwidth=4 expandtab
