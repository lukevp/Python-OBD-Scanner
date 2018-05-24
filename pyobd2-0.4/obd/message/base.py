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

"""Implementation of base BusMessage and Message classes"""

from obd.util import *

class BusMessage(object):
    """Represents a complete, reassembled message transmitted on the
    OBD bus.
    
    On ISO15765 buses, a single bus message may contain multiple logical
    messages (see Message class).  On other (legacy) buses, a single
    bus message can contain only a single logical message.

    On ISO15765 buses, there is a clear distinction between frames
    (individual packets sent on the bus) and messages (reassembled from
    the frames, sometimes by the interface).  On other (legacy) buses,
    bus messages are sometimes used as frames (i.e., in SIDs $03 and $09)
    but still called "messages" by specifications.  We consistently
    refer to these messages as "frames".  Therefore, in such instances,
    this object represents the reassembled larger message, and its
    constituent "frames" are what the specifications refer to as the
    multiple messages in the response.  See LegacyFrame and its
    SID-specific subclasses for more detail.

    header -- a Header instance containing information on the sender
        and intended receiver for this message (see Header class)
    data_bytes -- the complete, defragmented data contained in the
        bus message (exclusive of the header)
    frames -- a list of the raw frames received, prior to defragmentation
    protocol -- a Protocol instance specifying the bus protocol in
        which this message was received (see Protocol class)
    incomplete -- a boolean indicating whether any of the frames were
        missing or had errors
    sid() -- the SID of the bus message (whether request or response)
    is_response() -- a boolean indicating whether this message is a
        request or a response
    """
    OBD_RESPONSE_BIT = 0x40
    SID = 0
    PID = 1  # when applicable

    def __init__(self, header, data_bytes, frames):
        self.header = header
        self.data_bytes = data_bytes
        self.frames = frames
        self.protocol = self.header.protocol
        self.incomplete = (None in self.data_bytes)
        return
    def sid(self):
        """Return the SID for the given bus message (request or response)
        """
        return self.data_bytes[self.SID] & ~self.OBD_RESPONSE_BIT
    def is_response(self):
        """Return whether this bus message is an OBD request (False) or
        response (True).
        """
        return (self.data_bytes[self.SID] & self.OBD_RESPONSE_BIT) != 0
    def __str__(self):
        byte_str = " ".join(["%02X" % b for b in self.data_bytes])
        return "%s: %s" % (str(self.header), byte_str)

        
class Message(object):
    """Represents a single logical OBD message.
    
    On buses (such as ISO15765) that allow multiple requests to
    be issued in a single message, a single bus message (see
    BusMessage class) can convey multiple logical messages,
    up to one for each request.  On other (legacy) buses, a
    single bus message conveys only a single logical message.
    
    bus_message -- the bus message in which this logical message
        was transmitted (see BusMessage class)
    offset -- the offset within the bus message at which this
        logical message begins (see BusMessage class)
    data_bytes -- the raw bytes of this message, exclusive of
        any header
    length -- set by Message subclasses that encapsulate fixed-length
        messages, otherwise interchangeable with len(data_bytes)
    sid -- the SID of the message
    pid -- the PID of the message, or None if not applicable
    incomplete -- a boolean indicating whether any of the bytes
        are missing due to lost frames or errors
    
    byte() -- returns the byte at the given position, e.g. "A"
        is the first data byte, "B" is the second, etc.
    bit() -- returns the boolean of the bit at the given position,
        e.g., "A7" is the high bit of the first data byte,
        "D0" is the the low bit of the fourth data byte, etc.
    """
    length = None  # usually set by subclasses (when fixed)
    
    def __init__(self, bus_message, offset, pid=None):
        self.bus_message = bus_message
        self.offset = offset
        if self.length == None:
            self.data_bytes = self.bus_message.data_bytes[offset:]
            self.length = len(self.data_bytes)
        else:
            self.data_bytes = self.bus_message.data_bytes[offset:offset+self.length]
        self.sid = self.bus_message.sid()
        self.pid = pid
        self.incomplete = (None in self.data_bytes)
        return

    def byte(self, label):
        """Return the response byte given its OBD label, e.g. 'A', 'B', etc.
        """
        # "A" is the first byte after the response prefix, "D" is the fourth.
        index = ord(label) - ord("A")
        return self.data_bytes[index]

    def bit(self, label):
        """Return the response bit given its OBD label, e.g., 'A7', 'D3'.
        """
        byte = self.byte(label[:1])
        index = int(label[1:])
        return (byte & (1 << index)) != 0  # return a boolean for the bit

    def decode_string(byte_list):
        """Convert a list of bytes into a string
        """
        return "".join([chr(c) for c in byte_list if c != 0])
    decode_string = staticmethod(decode_string)
    
    def decode_integer(byte_list):
        """Convert a list of bytes into an integer
        """
        value = 0
        for b in byte_list:
            value <<= 8
            value += b
        return value
    decode_integer = staticmethod(decode_integer)
    
    def __str__(self):
        if self.pid is None:
            pidstr = ""
        else:
            pidstr = " PID $%X" % self.pid
        bytestr = " ".join(["%02X" % x for x in self.data_bytes])
        str = "SID $%X%s [%s]" % (self.sid, pidstr, bytestr)
        return str

"""
lengths = {
    0x02: { # SID $02
        0x00: 4,
        0x20: 4,
        0x40: 4,
        0x60: 4,
        0x80: 4,
        0xA0: 4,
        0xC0: 4,
        0xE0: 4,
    }
}
"""

# vim: softtabstop=4 shiftwidth=4 expandtab
