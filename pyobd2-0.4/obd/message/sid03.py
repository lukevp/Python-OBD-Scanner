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

"""Support for Service $03 (Request Emission-Related Diagnostic Trouble
Codes) requests and responses"""

from obd.protocol import LegacyFrame
from obd.message import register_response_class
from obd.message.response import VariableLengthResponse
from obd.util import untested

###################################
# Message reassembly

class LegacyFrameSid03(LegacyFrame):
    """Represents a "frame" in a legacy (non-ISO15765) response to a
    Service $03 request.
    
    See LegacyFrame for a discussion on the definition of "frame" in this
    context.

    raw_bytes -- the complete set of raw bytes making up the frame,
        including header and any checksum bytes
    header -- an instance of the appropriate protocol-specific Header
        subclass encapsulating the header bytes
    data_bytes -- the set of data bytes in the frame, excluding header
        and any checksum bytes
    checksum -- the checksum byte for the legacy frame
    
    assemble_message() -- Return the reassembled bytes given the full
        set of received frames.
    """
    def sequence_length(self):
        """Return the number of frames in the sequence:  None
        since the length is not known.
        
        The length is not specified in any legacy SID $03 frame.
        """
        untested("non-CAN SID 03 sequence length")
        return None  # variable number of messages (frames) in a response
    def assemble_message(self, frames):
        """Return the reassembled bytes given the full set of received
        frames.

        Reassemble the data contained in the individual frames into
        the list of bytes comprising the complete message, excluding
        any frame headers or footers.
        
        frames -- the list of frames in the sequence
        """
        untested("non-CAN SID 03 reassembly")
        # include the SID only once, at the beginning of the reassembled message
        result = [self.data_bytes[self.SID]]  # SID
        for frame in frames:
            if frame == None:
                untested("handling missing frame")
                # insert None for each missing byte in a missing frame
                result += [None] * (len(self.data_bytes) - (self.SID+1))
            else:
                untested("assembling non-CAN frame")
                result += frame.data_bytes[self.SID+1:]  # DTCs in each message
        return result
LegacyFrame._classes[0x03] = LegacyFrameSid03
LegacyFrame._classes[0x07] = LegacyFrameSid03  # SID $07 has identical format to SID $03


###################################
# Diagnostic Trouble Codes

class DTC(object):
    """Encapsulates a single Diagnostic Trouble Code (DTC)
    
    value -- the numeric value of the DTC (0 = none)
    """
    def __init__(self, value):
        self.value = value
        if not self.value:
            untested("null DTC")
        return
    def __str__(self):
        if not self.value:
            untested("null DTC")
            return "None"
        numeric = (self.value & 0x3FFF)
        alpha = (self.value >> 14) & 3
        alpha = "PCBU"[alpha]
        return "%s%04X" % (alpha, numeric)


class DTCResponse(VariableLengthResponse):
    """Encapsulates the response to a DTC request
    
    dtc -- a list of the DTCs, each DTC represented by a list of
        of two bytes
    """
    item_length = 2

    def __init__(self, message_data, offset, pid):
        VariableLengthResponse.__init__(self, message_data, offset, pid)
        self.items = self._get_item_bytes()
        dtcs = [self._decode_item(i) for i in self.items]
        self.dtcs = [d for d in dtcs if d.value]
        return
    
    def __str__(self):
        return "DTC=%s" % str([str(d) for d in self.dtcs])

    def _decode_item(self, item):
        return DTC(self.decode_integer(item))


###################################
# Registration

register_response_class(sid=0x03, pid=None, cls=DTCResponse)


# vim: softtabstop=4 shiftwidth=4 expandtab
