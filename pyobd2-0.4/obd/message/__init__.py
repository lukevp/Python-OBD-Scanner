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
This submodule manages the interpretation of data transmitted to and
received from the OBD bus.  It provides support for the automatic
reassembly of multi-frame messages contains logic for converting the
raw data into useable Python objects.

For details on the specific Python objects created to encapsulate the
various OBD messages, see sid01.py...sid09.py.  To register your own
classes to handle OBD messages:

register_message_class() -- registers a Message subclass for the given
    SID and PID (or equivalent), either a request or a response
register_response_class() -- a convenience function for registering a
    response (see Response class)

To create these objects by hand given a reassembled bus message:

create() -- creates an instance of the appropriate registered Message
    class

To send requests to the OBD bus, create one of the following to pass
to interface.send_request():

OBDRequest -- to send an OBD SID/PID request
RawRequest -- to send an arbitrary sequence of bytes
"""

_message_classes = {}

def register_message_class(sid, pid, response, message_class, override=False):
    """Register a Message subclass for encapsulating an OBD message of
    the given SID and PID (or equivalent).
    
    An instance of the specified class will be created to encapsulate each
    message received by the interface when it is configured to return
    "obd_messages" (the default).
    
    sid -- the Service or Mode ID
    pid -- the Parameter ID for the specific SID, or None if not applicable
    response -- a boolean indicating whether the class to be registered
        encapsulates a request (False) or a response (True)
    message_class -- the class (a subclass of Message) to register;
        it is good practice to register a subclass of Response for
        responses.
    override -- clients should generally set this to True if they wish to
        override built-in classes; it defaults to False to prevent any
        inadvertent overriding.
    """
    global _message_classes
    try:
        sid_classes = _message_classes[sid]
    except KeyError:
        if pid == None:
            sid_classes = [None, None]
        else:
            sid_classes = {}
        _message_classes[sid] = sid_classes
    
    if pid == None:
        assert isinstance(sid_classes, list), "attempting to register a class without a PID"
    else:
        assert isinstance(sid_classes, dict), "attempting to register a class with a PID"
        try:
            pid_classes = sid_classes[pid]
        except KeyError:
            pid_classes = [None, None]
            sid_classes[pid] = pid_classes
        sid_classes = pid_classes

    index = (response == True)

    # Allow intentional overriding, but yell in case of accidental override
    if override == False:
        assert(sid_classes[index] == None), "attempting to override a registered message"

    sid_classes[index] = message_class
    return


def register_response_class(sid, pid, cls):
    """Register a Response subclass for encapsulating an OBD response for
    the given SID and PID (or equivalent).
    
    This is a convenience function used for brevity elsewhere.
    """
    return register_message_class(sid, pid, True, cls)


from obd.message.base import BusMessage


def create(bus_message, offset=BusMessage.PID):
    """Create an OBD message object from a bus message.
    
    This function creates an instance of the appropriate registered
    Message class.  This is usually called automatically by the interface,
    which is configured to return "obd_messages" by default.
    
    If necessary, a client may call this explicitly via
    obd.message_create(). In cases where a bus message contains more than
    one logical message, this function is called with increasing offsets
    for each logical message.
    
    bus_message -- the complete OBD message received from the bus, as
        returned by an interface when configured to return "bus_messages"
    offset -- the position within the bus message at which the desired
        logical message begins
    """
    sid = bus_message.sid()
    pid = None
    index = bus_message.is_response()
    try:
        sid_classes = _message_classes[sid]
        if isinstance(sid_classes, dict):
            # if this SID uses PIDs, the first byte is the PID
            pid = bus_message.data_bytes[offset]
            offset += 1
            sid_classes = sid_classes[pid]
        else:
            # creating message for SID w/o PID
            pass
        message_class = sid_classes[index]
    except KeyError:
        message_class = Message
    return message_class(bus_message, offset, pid)


__all__ = ["create", "register_message_class", "register_response_class"]

from obd.message.base import Message
from obd.message.request import RawRequest, OBDRequest
from obd.message.response import Response

# Register the specific classes
from obd.message.sid01 import *
from obd.message.sid03 import *
from obd.message.sid09 import *


# vim: softtabstop=4 shiftwidth=4 expandtab                                     
