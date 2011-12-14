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

"""Support for Service $09 (Request Vehicle Information) requests and
responses"""

from obd.protocol import LegacyFrame
from obd.message import register_response_class
from obd.message.response import VariableLengthResponse
from obd.message.sid01 import PIDSupportResponse
from obd.message.value import *
from obd.exception import J1699Failure
from obd.util import untested, unimplemented

class Service09Response(VariableLengthResponse):
    """The base class of substantive Service $09 responses
    (i.e., excluding MessageCount messages), variable-length
    responses whose contents can be completely represented
    by Value objects
    
    values -- the list of values contained in the response,
        each value represented as an instance of a Value
        subclass
        
    See parent classes (e.g., Message) for other attributes.
    """
    _value_labels = []
    _value_type = Value
    def __init__(self, message_data, offset, pid):
        VariableLengthResponse.__init__(self, message_data, offset, pid)
        self.items = self._get_item_bytes()
        raw_values = [self._decode_item(i) for i in self.items]
        self._create_values(raw_values)
        return
    
    def _create_values(self, raw_values):
        self.values = []
        for label, raw_value in zip(self._value_labels, raw_values):
            value = self._value_type(label, raw_value=raw_value)
            self.values.append(value)
        if len(raw_values) > len(self.values):
            unimplemented("trailing items ignored")
        return

    def _decode_item(self, item):
        return item

    def __str__(self):
        return "\n".join([str(v) for v in self.values])


# Service $09 INFOTYPEs
SUPPORT  = 0x00
MC_VIN   = 0x01  # non-CAN only
VIN      = 0x02
MC_CALID = 0x03  # non-CAN only
CALID    = 0x04
MC_CVN   = 0x05  # non-CAN only
CVN      = 0x06
MC_IPT   = 0x07  # non-CAN only
IPT      = 0x08
MC_ECUNAME = 0x09  # non-CAN only
ECUNAME  = 0x0A
IPT2     = 0x0B  # compression ignition engines MY 2010 and later (CAN only)


###################################
# Message reassembly

class LegacyFrameSid09(LegacyFrame):
    """Represents a "frame" in a legacy (non-ISO15765) response to a
    Service $09 request.
    
    See LegacyFrame for a discussion on the definition of "frame" in this
    context.

    raw_bytes -- the complete set of raw bytes making up the frame,
        including header and any checksum bytes
    header -- an instance of the appropriate protocol-specific Header
        subclass encapsulating the header bytes
    data_bytes -- the set of data bytes in the frame, excluding header
        and any checksum bytes
    checksum -- the checksum byte for the legacy frame
    
    pid() -- Return the PID for this SID $09 frame
    assemble_message() -- Return the reassembled bytes given the full
        set of received frames.
    """
    PID = 1  # byte #2 is PID (or INFTYP to be precise) 
    MC  = 2  # byte #3 is MessageCount
    _sequence_lengths = {
        # Don't include (non-CAN) MessageCount requests, since they're always
        # a single frame which doesn't contain a sequence number.
        SUPPORT: 1,   # 1 message (frame) for a INFTYP Supported request
        VIN: 5,       # 5 messages (frames) for a VIN request
        CALID: None,  # variable number of messages (frames) for a calibration ID request
        CVN: None,    # variable number of messages (frames) for a CVN request
        IPT: 8,       # 8 messages (frames) for an IPT request
        ECUNAME: 5,   # 5 messages (frames) for an ECUNAME request
    }
    
    def _sequence_key(self):
        """Return the bytes comprising the sequence key for this frame.
        
        See Frame._sequence_key() for background.

        The header (which includes the address of the transmitter) + SID
        and PID identify which message a legacy SID $09 frame belongs to.
        """
        return self.header.raw_bytes + self.data_bytes[self.SID:self.PID+1]
    def sequence_number(self, last_sn):
        """Return the position of this frame in the sequence, or
        None if there is no specified ordering.
        
        For SID $09 responses apart from MessageCount responses, the MC
        byte is the 1-based sequence number.  MessageCount responses use
        that byte as their sole data.
        """
        if self.pid() in self._sequence_lengths:
            seq = self.data_bytes[self.MC] - 1  # MessageCount
        else:
            seq = None  # no sequence number for MessageCount requests
        return seq
    def sequence_length(self):
        """Return the number of frames in the sequence, or None
        if the length is not known.
        
        The length is only known for the SID $09 responses with a
        constant length assigned by specification.
        """
        try:
            frames = self._sequence_lengths[self.pid()]
        except KeyError:
            frames = 1  # MessageCount requests get a single-frame response
        return frames
    def data_length(self):
        """Return the number of data bytes contained in the complete,
        reassembled sequence, or None if this frame has no such
        information.

        The length is only known for the SID $09 responses with a
        constant length assigned by specification.
        """
        untested("non-CAN SID 09 data length")
        try:
            frames = self._sequence_lengths[self.pid()]
            if frames:
                untested("known number of frames in non-CAN SID 09 message")
                length = frames * 4 + 2  # 4 data bytes per frame + SID/PID for message
            else:
                untested("variable number of frames in non-CAN SID 09 message")
                length = None  # variable number of bytes
        except KeyError:
            untested("non-CAN SID 09 MessageCount query")
            length = 3  # SID+PID + MessageCount byte for MessageCount requests
        return length
    def pid(self):
        """Return the PID for this SID $09 frame"""
        return self.data_bytes[self.PID]
    def assemble_message(self, frames):
        """Return the reassembled bytes given the full set of received
        frames.

        Reassemble the data contained in the individual frames into
        the list of bytes comprising the complete message, excluding
        any frame headers or footers.
        
        frames -- the list of frames in the sequence
        """
        if self.pid() in self._sequence_lengths:
            # include the SID and PID only once, at the beginning of the
            # reassembled message
            result = self.data_bytes[self.SID:self.PID+1]  # SID+PID
            for frame in frames:
                if frame == None:
                    untested("missing frames in non-CAN SID 09 message")
                    # insert None for each missing byte in a missing frame
                    result += [None] * (len(self.data_bytes) - (self.MC+1))
                else:
                    result += frame.data_bytes[self.MC+1:]  # skip SID/PID/MessageCount
        else:
            assert len(frames) == 1
            assert self.pid() in [MC_VIN, MC_CALID, MC_CVN, MC_IPT, MC_ECUNAME]
            # MessageCount requests are single-frame messages and don't have
            # any sequence number to skip
            result = self.data_bytes[:]
        return result
LegacyFrame._classes[0x09] = LegacyFrameSid09


###################################
# INFTYP $00 = SUPPORT

# PIDSupportResponse is used to report supported INFTYPs.


###################################
# INFTYP $01, $03, $05, $07, $09 = MC_*

class MessageCountResponse(ValueResponse):
    """Encapsulates the response to a message count
    request.
    """
    length = 1
    _value_factories = [Factory("MC", Value, "A")]
    # TODO: yell if we see an MC response on a CAN bus

def _mc_response(pid, label):
    """Create the PID-specific variant of the message count response"""
    response_class = value_response_variant(pid, MessageCountResponse)
    response_class._value_factories[0].label = label
    return response_class


###################################
# INFTYP $02 = VIN

class VINResponse(Service09Response):
    """Encapsulates the response to a VIN request.
    """
    item_length = 17
    _value_labels = ["VIN"]
    _value_type = TextValue

    def __init__(self, message_data, offset, pid):
        Service09Response.__init__(self, message_data, offset, pid)
        if len(self.items) != 1: raise J1699Failure("VIN NODI != 1", raw=self)
        return
    
    def _get_items_offset(self):
        if self.item_count_byte != None:
            offset = 1  # CAN only has a leading item_count byte
        else:
            offset = 3  # non-CAN have leading NULL padding
        return offset

    def _decode_item(self, item):
        return self.decode_string(item)


###################################
# INFTYP $04 = CALID

class CalibrationResponse(Service09Response):
    """Parent class for calibration responses (CALID/CVN),
    variable-length OBD responses whose contents are
    represented by ListValue objects.
    
    values -- the list of values contained in the response,
        each value represented as an instance of a ListValue
        object
        
    See parent classes (e.g., VariableLengthResponse) for other attributes.
    """
    def _create_values(self, raw_values):
        assert len(self._value_labels) == 1
        label = self._value_labels[0]
        value = self._value_type(label, raw_value=raw_values)
        self.values = [value]
        return

class CalibrationIDResponse(CalibrationResponse):
    """Encapsulates the response to a calibration ID request.
    """
    item_length = 16
    _value_labels = ["CALID"]
    _value_type = ListValue

    def _decode_item(self, item):
        return self.decode_string(item)


###################################
# INFTYP $06 = CVN

class CVNValue(ListValue):
    """Encapsulates a list of CVNs provided by a CVN response"""
    _value_fmt = "%08X"

class CVNResponse(CalibrationResponse):
    """Encapsulates the response to a calibration verification
    number (CVN) request.
    """
    item_length = 4
    _value_labels = ["CVN"]
    _value_type = CVNValue

    def _decode_item(self, item):
        return self.decode_integer(item)


###################################
# INFTYPE $08 = IPT

class IPTResponse(Service09Response):
    """Encapsulates the response to an In-Use Performance
    Tracking request
    """
    item_length = 2
    
    _value_labels = [
        "OBDCOND",   # OBD monitoring conditions
        "IGNCNTR",   # Ignition counter
        "CATCOMP1",  # Catalyst monitor bank 1
        "CATCOND1",
        "CATCOMP2",  # Catalyst monitor bank 2
        "CATCOND2",
        "O2SCOMP1",  # O2 sensor monitor bank 1
        "O2SCOND1",
        "O2SCOMP2",  # O2 sensor monitor bank 2
        "O2SCOND2",
        "EGRCOMP",   # EGR or VVT monitor
        "EGRCOND",
        "AIRCOMP",   # Air monitor
        "AIRCOND",
        "EVAPCOMP",  # EVAP monitor
        "EVAPCOND",
        "SO2SCOMP1",  # Secondary O2 sensor bank 1
        "SO2SCOND1",
        "SO2SCOMP2",  # Secondary O2 sensor bank 2
        "SO2SCOND2"
    ]
    _value_type = CountValue

    def __init__(self, message_data, offset, pid):
        Service09Response.__init__(self, message_data, offset, pid)
        if len(self.items) != 16 and len(self.items) != 20:
            raise J1699Failure("IPT NODI != 16 or 20", raw=self)
        if len(self.items) > len(self._value_labels):
            raise DataError("IPT NODI too large", raw=self)
        return
    
    def _decode_item(self, item):
        return self.decode_integer(item)


###################################
# INFTYP $0A = ECUNAME

class ECUNameResponse(Service09Response):
    """Encapsulates the response to a ECU name request.
    """
    item_length = 20
    _value_labels = ["ECU", "ECUNAME"]
    _value_type = TextValue

    def __init__(self, message_data, offset, pid):
        Service09Response.__init__(self, message_data, offset, pid)
        return

    def _get_item_bytes(self):
        items = Service09Response._get_item_bytes(self)
        if len(items) != 1: raise J1699Failure("ECUNAME NODI != 1", raw=self)
        item = items[0]
        # The contents of the single message item are broken into two
        # logical fields, separated by "-"
        delim_pos = 4
        items = [item[:delim_pos], item[delim_pos+1:]]
        return items
    
    def _decode_item(self, item):
        return self.decode_string(item)


###################################
# INFTYPE $0B = Diesel IPT

class DieselIPTResponse(Service09Response):
    """Encapsulates the response to an In-Use Performance
    Tracking request for diesel (compression ignition)
    engines
    """
    item_length = 2
    
    _value_labels = [
        "OBDCOND",    # OBD monitoring conditions
        "IGNCNTR",    # Ignition counter
        "HCCATCOMP",  # NMHC catalyst monitor
        "HCCATCOND",
        "NCATCOMP",   # NOx catalyst monitor
        "NCATCOND",
        "NADSCOMP",   # NOx absorber monitor
        "NADSCOND",
        "PMCOMP",     # PM filter
        "PMCOND",
        "EGSCOMP",    # Exhaust gas sensor
        "EGSCOND",
        "EGRCOMP",    # EGR or VVT monitor
        "EGRCOND",
        "BPCOMP",     # Boost pressure monitor
        "BPCOND",
    ]
    _value_type = CountValue

    def __init__(self, message_data, offset, pid):
        untested("Diesel IPT response")
        Service09Response.__init__(self, message_data, offset, pid)
        if len(self.items) != 16:
            raise J1699Failure("IPT NODI != 16", raw=self)
        return
    
    def _decode_item(self, item):
        return self.decode_integer(item)


###################################
# Registration

register_response_class(sid=0x09, pid=0x00, cls=PIDSupportResponse)
register_response_class(sid=0x09, pid=0x01, cls=_mc_response(0x01, "MC_VIN"))
register_response_class(sid=0x09, pid=0x02, cls=VINResponse)
register_response_class(sid=0x09, pid=0x03, cls=_mc_response(0x03, "MC_CALID"))
register_response_class(sid=0x09, pid=0x04, cls=CalibrationIDResponse)
register_response_class(sid=0x09, pid=0x05, cls=_mc_response(0x05, "MC_CVN"))
register_response_class(sid=0x09, pid=0x06, cls=CVNResponse)
register_response_class(sid=0x09, pid=0x07, cls=_mc_response(0x07, "MC_IPT"))
register_response_class(sid=0x09, pid=0x08, cls=IPTResponse)
register_response_class(sid=0x09, pid=0x09, cls=_mc_response(0x09, "MC_ECUNM"))
register_response_class(sid=0x09, pid=0x0A, cls=ECUNameResponse)
register_response_class(sid=0x09, pid=0x0B, cls=DieselIPTResponse)

# vim: softtabstop=4 shiftwidth=4 expandtab
