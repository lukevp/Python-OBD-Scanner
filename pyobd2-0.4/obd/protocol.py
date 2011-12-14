#!usr/bin/env python -3
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
This submodule provides the abstraction for supported OBD protocols,
allowing raw bytes to be encapsulated in protocol-specific objects
with a protocol-neutral API.  These objects can then be passed
on to the "message" submodule for further interpretation.

Instances of Protocol subclasses may be passed to Interfaces to
indicate when a specific protocol should be used, and likewise
instances of Protocol subclasses are returned by Interfaces to
indicate which protocol is currently in use:

  PWM
  VPW
  ISO9141_2
  ISO14230_4 (or KWP)
  ISO15765_4 (often imprecisely called "CAN")
  SAE_J1939 (largely unimplemented)

For example:

if interface.get_protocol() != ISO15765_4():
    interface.set_protocol(ISO15765_4())
"""

from obd.util import *
from obd.message.base import BusMessage

class Protocol(object):
    """Base class for specifying and supporting OBD protocols
    
    name -- the human-readable name of the protocol
    baud -- the baud rate used to communicate with the vehicle
    header_size -- the number of header bytes in each message
        in the protocol
    
    create_frame() -- encapsulate the given raw bytes in a
        frame of the appropriate class for the protocol.
        Note that Protocol.create_frame() has special
        behavior compared to the overridden versions.
    
    == and != are defined so that _instances_ of the various
    protocol subclasses can be compared to determine whether
    they specify the same protocol
    """
    def __init__(self, name, baud, header_size):
        """name -- the human-readable name of the protocol
        baud -- the baud rate used to communicate with the vehicle
        header_size -- the number of header bytes in each message
            in the protocol
        """
        debug(name)
        self.name = name
        self.baud = baud
        self.header_size = header_size
        return
    def __eq__(self, other):
        """Consider identical instances to be equal"""
        if not isinstance(other, Protocol): return False
        # We can't really test for specific type, since that would break the comparison of
        # subclasses that are equivalent.  The safety net here is that self.name should
        # be differ between distinct protocols.
        return vars(self) == vars(other)
    def __ne__(self, other):
        return not (self == other)
    def __hash__(self):                # needed for Python 3.x when __eq__ is overridden
        """Consider identical instances to be equal
        
        WARNING: if you change a Protocol object in a dict or other hash
        table, you'll break the dict, since the hash will no longer find
        the object.  So don't do it.
        """
        return hash(repr(vars(self)))  # dicts aren't hashable, so hash the repr instead
    def __str__(self):
        """Return the human-readable name of the protocol"""
        return self.name
    def create_header(self, raw_bytes):
        """Return the appropriate protocol-specific header encapsulating
        the header bytes in the given data
        
        Must be implemented by concrete Protocol subclasses.
        """
        raise NotImplementedError()
        return
    def create_frame(self, raw_bytes):
        """Return a generic Frame object encapsulating the given data.

        This should be explicitly called by interfaces that wish to skip
        this library's multi-frame reassembly process, such as interfaces
        that reassemble CAN messages themselves.  (Protocol subclasses
        override this so that instances can provide protocol-specific
        reassembly.)
        
        raw_bytes -- the raw bytes to encapsulate
        """
        header = self.create_header(raw_bytes)
        return Frame(raw_bytes, header)  # use the generic Frame class to skip reassembly


class Header(object):
    """Base class for abstracting protocol-specific message headers
    
    protocol -- an instance of the Protocol subclass associated with this
        header
    raw_bytes -- the raw header bytes (of appropriate protocol-specific
        length)
    length -- the number of bytes in the header
    tx_id -- the ID of the transmitting ECU
    rx_id -- the ID of the ECU to which the message is addressed
    addr_mode -- the addressing mode specified in the header (e.g.,
        functional or physical)
    priority -- the priority of the message
    
    Eventually this should support some protocol-neutral representation of
    IDs, addressing mode, etc.
    """
    def __init__(self, protocol, raw_bytes):
        """protocol -- an instance of the Protocol subclass asssociated with
            this header
        raw_bytes -- the raw bytes of the entire message, from which the
            header bytes will be read"""
        self.protocol = protocol
        self.raw_bytes = raw_bytes
        self.length = len(raw_bytes)
        self.tx_id = None
        self.rx_id = None
        self.addr_mode = None
        self.priority = None
        return
    def __str__(self):
        return "".join(["%02X" % b for b in self.raw_bytes])

        
class Frame(object):
    """Base class for abstracting protocol-specific frame reassembly
    
    On ISO15765 buses, there is a clear distinction between frames
    (individual packets sent on the bus) and messages (reassembled from
    the frames, sometimes by the interface).  On other (legacy) buses,
    bus messages are sometimes used as frames (i.e., in SIDs $03 and $09)
    but still called "messages" by specifications.  We consistently
    refer to these messages as "frames" and the reassembled, complete
    response as a "message".  This object represents "frames" as we use
    the term.
    
    raw_bytes -- the complete set of raw bytes making up the frame,
        including header and any checksum bytes
    header -- an instance of the appropriate protocol-specific Header
        subclass encapsulating the header bytes
    data_bytes -- the set of data bytes in the frame, excluding header
        and any checksum bytes
    
    assemble_message() -- Return the reassembled bytes given the full
        set of received frames.
    """
    def __init__(self, raw_bytes, header):
        """raw_bytes -- the raw data to encapsulate
        header -- an instance of the appropriate Header subclass
            encapsulating the header bytes in the given data
        """
        self.raw_bytes = raw_bytes
        self.header = header
        self.data_bytes = raw_bytes[header.length:]
        return
    def sequence_key(self):
        """Return a hashable representation of the sequence key.
        
        The sequence key identifies which "sequence" of frames
        (message) this frame belongs to, as an interface may receive
        interleaved frames belonging to different sequences."""
        return "".join([chr(c) for c in self._sequence_key()])
    def _sequence_key(self):
        """Return the bytes comprising the sequence key for this frame.
        
        The sequence key identifies which "sequence" of frames
        (message) this frame belongs to, as an interface may receive
        interleaved frames belonging to different sequences.
        
        Subclasses should override this as appropriate.
        """
        return self.header.raw_bytes
    def sequence_number(self, last_sn):
        """Return the position of this frame in the sequence, or
        None if there is no specified ordering.
        
        last_sn -- the most recently seen sequence number; this
            is necessary to determine the actual sequence number
            when the frame uses too few bits to encode the range
            of sequence numbers used by a message
        """
        return None  # default to no sequence number
    def sequence_length(self):
        """Return the number of frames in the sequence, or None
        if the length is not known.
        """
        return 1  # default to single-frame message
    def data_length(self):
        """Return the number of data bytes contained in the complete,
        reassembled sequence, or None if this frame has no such
        information.
        """
        untested("non-CAN frame or CAN on non-ELM")
        return len(self.data_bytes)  # default to length of data in frame
    def assemble_message(self, frames):
        """Return the bytes contained in the complete, reassembled
        sequence.

        Reassemble the data contained in the individual frames into
        the list of bytes comprising the complete message, excluding
        any frame headers or footers.
        
        frames -- the list of frames in the sequence
        """
        return self.data_bytes  # default to a single-frame message


# MARK: -

class LegacyProtocol(Protocol):
    """Base class for specifying and supporting legacy (non-ISO15765)
    protocols.
    
    name -- the human-readable name of the protocol
    baud -- the baud rate used to communicate with the vehicle
    header_size -- the number of header bytes in each message
        in the protocol
    
    create_frame() -- encapsulate the given raw bytes in a
        frame of the appropriate class for the legacy protocol.
    """
    def create_header(self, raw_bytes):
        """Return the appropriate protocol-specific header encapsulating
        the header bytes in the given data
        
        Must be implemented by concrete Protocol subclasses.
        """
        raise NotImplementedError()
        return
    def create_frame(self, raw_bytes):
        """Return the appropriate protocol-specific Frame object
        encapsulating the given data and reassembling it into a
        complete message.
        
        Note that for legacy (non-CAN) protocols, the specific Frame
        subclass will depend upon the SID.  See LegacyFrame.create()
        for details.
        
        raw_bytes -- the raw bytes to encapsulate
        """
        header = self.create_header(raw_bytes)
        return LegacyFrame.create(raw_bytes, header)


class LegacyFrame(Frame):
    """Represents a "frame" in a legacy (non-ISO15765) protocol.
    
    Note that legacy (non-ISO15765) protocols do not technically have
    "frames".  Instead, they define the responses to certain requests
    (SIDs $03 and $09) to be comprised of multiple individual messages
    that are interpreted collectively.  In other words, these individual
    messages function as frames, despite the ambiguous nomenclature.
    For clarity, we consistently refer to such messages as "frames"
    and the reassembled, complete response as the "message".

    raw_bytes -- the complete set of raw bytes making up the frame,
        including header and checksum bytes
    header -- an instance of the appropriate protocol-specific Header
        subclass encapsulating the header bytes
    data_bytes -- the set of data bytes in the frame, excluding header
        and checksum bytes
    checksum -- the checksum byte for the legacy frame
    """
    def __init__(self, raw_bytes, header):
        """raw_bytes -- the raw data to encapsulate
        header -- an instance of the appropriate Header subclass
            encapsulating the header bytes in the given data
        """
        Frame.__init__(self, raw_bytes, header)
        # With headers on, the last byte of legacy frames is the checksum
        # (NOTE: This may be ELM-specific.)
        self.checksum = self.data_bytes[-1]
        self.data_bytes = self.data_bytes[:-1]
        return

    SID = 0  # byte #1 of all legacy frames is the SID
    def _sequence_key(self):
        """Return the bytes comprising the sequence key for this frame.
        
        See Frame._sequence_key() for background.

        The header (which includes the address of the transmitter) + SID
        identify which message a legacy frame belongs to.
        """
        return self.header.raw_bytes + [self.data_bytes[self.SID]]

    _classes = {}  # subclasses are defined and registered in SID-specific files
    def create(raw_bytes, header):
        """
        Create the appropriate SID-specific subclass of LegacyFrame given
        the bytes received.
        
        The various subclasses are defined and registered in their
        respective SID-specific files (e.g., SIDs $03 and $09).
        
        raw_bytes -- the complete set of raw bytes making up the frame,
            including header and any checksum bytes
        header -- an instance of the appropriate protocol-specific Header
            subclass encapsulating the header bytes
        """
        sid = raw_bytes[header.length + LegacyFrame.SID]
        sid &= ~BusMessage.OBD_RESPONSE_BIT
        try:
            frame_class = LegacyFrame._classes[sid]
        except KeyError:
            frame_class = LegacyFrame
        return frame_class(raw_bytes, header)
    create = staticmethod(create)


class SAE_J1850(LegacyProtocol):
    """Base class for specifying and supporting SAE J1850 legacy
    protocols (both VPW and PWM).
    
    name -- the human-readable name of the protocol
    baud -- the baud rate used to communicate with the vehicle
    header_size -- the number of header bytes in each message
        in the protocol
    signaling -- indicates whether VPW or PWM signaling is
        used on the OBD bus
    
    create_frame() -- encapsulate the given raw bytes in a
        frame of the appropriate class for the protocol.
    """
    signalings = [ "PWM", "VPW" ]
    def __init__(self, signaling, baud):
        """signaling -- PWM or VPW
        baud -- the baud rate used to communicate with the vehicle
        """
        if signaling not in self.signalings: raise ValueError
        name = "SAE J1850 %s (%0.1f Kbaud)" % (signaling, baud/1000.0)
        LegacyProtocol.__init__(self, name, baud, header_size=3)
        self.signaling = signaling
        return


class PWM(SAE_J1850):
    """Represents the SAE-J1850 PWM protocol
    
    name -- the human-readable name of the protocol
    baud -- the baud rate used to communicate with the vehicle
    header_size -- the number of header bytes in each message
        in the protocol
    
    create_frame() -- encapsulate the given raw bytes in a
        frame of the appropriate class for the legacy protocol.
    """
    def __init__(self):
        SAE_J1850.__init__(self, "PWM", 41600)
        return
    def create_header(self, raw_bytes):
        """Return the appropriate protocol-specific header encapsulating
        the header bytes in the given data
        """
        untested("PWM protocol")
        return PWMHeader(self, raw_bytes)

class PWMHeader(Header):
    """Protocol-specific class for encapsulating SAE-J1850 PWM message headers
    
    protocol -- an instance of the PWM class
    raw_bytes -- the raw header bytes
    length -- the number of bytes in the header (3 for PWM)
    tx_id -- the ID of the transmitting ECU
    rx_id -- the ID of the ECU to which the message is addressed
    addr_mode -- the addressing mode specified in the header (e.g.,
        functional or physical)
    priority -- the priority of the message
    
    Eventually this should support some protocol-neutral representation of
    IDs, addressing mode, etc.
    """
    def __init__(self, protocol, raw_bytes):
        """protocol -- an instance of the Protocol subclass asssociated with
            this header
        raw_bytes -- the raw bytes of the entire message, from which the
            header bytes will be read"""
        untested("PWM header")
        Header.__init__(self, protocol, raw_bytes[0:3])
        # 0x61
        # 0x6A
        self.tx_id = self.raw_bytes[2]
        return
    
class VPW(SAE_J1850):
    """Represents the SAE-J1850 VPW protocol
    
    name -- the human-readable name of the protocol
    baud -- the baud rate used to communicate with the vehicle
    header_size -- the number of header bytes in each message
        in the protocol
    
    create_frame() -- encapsulate the given raw bytes in a
        frame of the appropriate class for the legacy protocol.
    """
    def __init__(self):
        SAE_J1850.__init__(self, "VPW", 10400)
        return
    def create_header(self, raw_bytes):
        """Return the appropriate protocol-specific header encapsulating
        the header bytes in the given data
        """
        untested("VPW protocol")
        return VPWHeader(self, raw_bytes)

class VPWHeader(Header):
    """Protocol-specific class for encapsulating SAE-J1850 VPW message headers
    
    protocol -- an instance of the VPW class
    raw_bytes -- the raw header bytes
    length -- the number of bytes in the header (3 for VPW)
    tx_id -- the ID of the transmitting ECU
    rx_id -- the ID of the ECU to which the message is addressed
    addr_mode -- the addressing mode specified in the header (e.g.,
        functional or physical)
    priority -- the priority of the message
    
    Eventually this should support some protocol-neutral representation of
    IDs, addressing mode, etc.
    """
    def __init__(self, protocol, raw_bytes):
        """protocol -- an instance of the Protocol subclass asssociated with
            this header
        raw_bytes -- the raw bytes of the entire message, from which the
            header bytes will be read"""
        Header.__init__(self, protocol, raw_bytes[0:3])
        # 0x68
        # 0x6A
        self.tx_id = self.raw_bytes[2]
        return

class ISO9141_2(LegacyProtocol):
    """Represents the ISO 9141-2 protocol
    
    name -- the human-readable name of the protocol
    baud -- the baud rate used to communicate with the vehicle
    header_size -- the number of header bytes in each message
        in the protocol
    
    create_frame() -- encapsulate the given raw bytes in a
        frame of the appropriate class for the legacy protocol.
    """
    def __init__(self):
        LegacyProtocol.__init__(self, "ISO 9141-2 (5 baud init, 10.4 Kbaud)", baud=10400, header_size=3)
        return
    def create_header(self, raw_bytes):
        """Return the appropriate protocol-specific header encapsulating
        the header bytes in the given data
        """
        return ISO9141Header(self, raw_bytes)

class ISO9141Header(VPWHeader):
    """Protocol-specific class for encapsulating ISO-9141 message headers.
    ISO-9141 uses identical header encoding as SAE-J1850 VPW.
    
    protocol -- an instance of the ISO9141_2 class
    raw_bytes -- the raw header bytes
    length -- the number of bytes in the header (3 for PWM)
    tx_id -- the ID of the transmitting ECU
    rx_id -- the ID of the ECU to which the message is addressed
    addr_mode -- the addressing mode specified in the header (e.g.,
        functional or physical)
    priority -- the priority of the message
    
    Eventually this should support some protocol-neutral representation of
    IDs, addressing mode, etc.
    """
    pass

class ISO14230_4(LegacyProtocol):
    """Represents the ISO 14230-4 ("KWP") protocols
    
    name -- the human-readable name of the protocol
    baud -- the baud rate used to communicate with the vehicle
    header_size -- the number of header bytes in each message
        in the protocol
    
    create_frame() -- encapsulate the given raw bytes in a
        frame of the appropriate class for the legacy protocol.
    """
    inits = { "FAST": "fast", "5BAUD": "5 baud" }
    def __init__(self, init):
        """init -- the initialization baud rate: FAST or 5BAUD"""
        if not init in self.inits: raise ValueError()
        LegacyProtocol.__init__(self, "ISO 14230-4 KWP (%s init, 10.4 Kbaud)" % self.inits[init], baud=10400, header_size=3)
        self.init = init
    pass
    def create_header(self, raw_bytes):
        """Return the appropriate protocol-specific header encapsulating
        the header bytes in the given data
        """
        untested("ISO14230 protocol")
        return ISO14230Header(self, raw_bytes)

class ISO14230Header(Header):
    """Protocol-specific class for encapsulating ISO 14230-4 message headers
    
    protocol -- an instance of the ISO 14230-4 class
    raw_bytes -- the raw header bytes
    length -- the number of bytes in the header (3 for ISO 14230-4)
    tx_id -- the ID of the transmitting ECU
    rx_id -- the ID of the ECU to which the message is addressed
    addr_mode -- the addressing mode specified in the header (e.g.,
        functional or physical)
    priority -- the priority of the message
    
    Eventually this should support some protocol-neutral representation of
    IDs, addressing mode, etc.
    """
    def __init__(self, protocol, raw_bytes):
        """protocol -- an instance of the Protocol subclass asssociated with
            this header
        raw_bytes -- the raw bytes of the entire message, from which the
            header bytes will be read"""
        untested("ISO14230 header")
        Header.__init__(self, protocol, raw_bytes[0:3])
        # 0xC0 + data_len (after header)
        # 0x33
        self.tx_id = self.raw_bytes[2]
        return
    

class KWP(ISO14230_4):
    """A convenience class, simply providing a synonym for ISO 14230-4"""
    pass


# MARK: -

class CAN(Protocol):
    """Base class for specifying and supporting CAN protocols
    (ISO 15765-4 and SAE J1939).
    
    name -- the human-readable name of the protocol
    baud -- the baud rate used to communicate with the vehicle
    header_size -- the number of header bytes in each message
        in the protocol
    data_format -- ISO 15765-4 or SAE J1939
    id_length -- 11 or 29 to represent 11-bit or 29-bit headers
    receive_id_length -- usually the same as id_length
    data_length -- the payload size for each frame; generally 8
    
    create_frame() -- encapsulate the given raw bytes in a
        frame of the appropriate class for the protocol.
    """
    data_formats = { "ISO15765_4": "ISO 15765-4", "SAE_J1939": "SAE J1939" }
    id_lengths = [ 11, 29 ]
    data_lengths = [ 8, None]  # None denotes variable DLC
    bauds = [ 500000, 250000, 125000, 50000 ]

    def __init__(self, data_format, id_length=29, receive_id_length=None, data_length=8, baud=500000):
        """data_format -- ISO15765_4 or SAE_J1939
        id_length -- 11 or 29 to represent 11-bit or 29-bit headers
            (default 29)
        data_length -- payload size of each frame (default 8 bytes)
        baud -- the baud rate used to communicate with the vehicle
            (default 500K)
        """
        if receive_id_length == None: receive_id_length = id_length
        if receive_id_length != id_length:
            unimplemented("CAN receive address length != transmit address length")

        if not data_format in self.data_formats: raise ValueError()
        if not id_length in self.id_lengths: raise ValueError()
        if not receive_id_length in self.id_lengths: raise ValueError()
        if not data_length in self.data_lengths: raise ValueError()
        if not baud in self.bauds: raise ValueError()

        Protocol.__init__(self, "%s CAN (%d bit ID, %d Kbaud)" % 
                          (self.data_formats[data_format], id_length, baud//1000),
                          baud,
                          header_size=4)

        self.data_format = data_format
        self.id_length = id_length
        self.receive_id_length = receive_id_length
        self.data_length = data_length
        return


class ISO15765_4(CAN):
    """Represents the ISO 15765-4 protocol
    
    name -- the human-readable name of the protocol
    baud -- the baud rate used to communicate with the vehicle
    header_size -- the number of header bytes in each message
        in the protocol
    
    create_frame() -- encapsulate the given raw bytes in a
        frame of the appropriate class for the legacy protocol.
    """
    def __init__(self, id_length=29, receive_id_length=None, data_length=8, baud=500000):
        """id_length -- 11 or 29 to represent 11-bit or 29-bit headers
            (default 29)
        data_length -- payload size of each frame (default 8 bytes)
        baud -- the baud rate used to communicate with the vehicle
            (default 500K)
        """
        CAN.__init__(self, "ISO15765_4",
                     id_length=id_length,
                     receive_id_length=receive_id_length,
                     data_length=data_length,
                     baud=baud)
        return
    def create_header(self, raw_bytes):
        """Return the appropriate protocol-specific header encapsulating
        the header bytes in the given data
        """
        return ISO15765Header(self, raw_bytes, self.id_length)
    def create_frame(self, raw_bytes):
        """Return the appropriate protocol-specific Frame object
        encapsulating the given data and reassembling it into a
        complete message.
        
        raw_bytes -- the raw bytes to encapsulate
        """
        # Interfaces that reassemble CAN messages themselves should instead
        # call Protocol.create_frame(protocol, raw_bytes) for CAN protocol messages
        # to skip this library's reassembly process.
        header = self.create_header(raw_bytes)
        return ISO15765Frame(raw_bytes, header)


class ISO15765Header(Header):
    """Protocol-specific class for encapsulating ISO 15765-4 message headers
    
    protocol -- an instance of the ISO15765_4 class
    raw_bytes -- the raw header bytes
    length -- the number of bytes in the header (4 for ISO 15765-4);
        technically, 11-bit CAN headers are just 3 nibbles, but the
        Interface class is responsible for padding them out to 4 bytes
    tx_id -- the ID of the transmitting ECU
    rx_id -- the ID of the ECU to which the message is addressed
    addr_mode -- the addressing mode specified in the header (e.g.,
        functional or physical)
    priority -- the priority of the message
    
    Eventually this should support some protocol-neutral representation of
    IDs, addressing mode, etc.
    """
    def __init__(self, protocol, raw_bytes, id_length):
        """protocol -- an instance of the Protocol subclass asssociated with
            this header
        raw_bytes -- the raw bytes of the entire message, from which the
            header bytes will be read"""
        Header.__init__(self, protocol, raw_bytes[0:4])
        if id_length == 11:
            self.priority = raw_bytes[2] & 0x0F  # always 7
            self.addr_mode = raw_bytes[3] & 0xF0  # 0xD0 = functional, 0xE0 = physical
            if self.addr_mode == 0xD0:
                untested("11-bit functional request from tester")
                self.tx_id = 0xF1  # made-up to mimic all other protocols
                self.rx_id = raw_bytes[3] & 0x0F  # usually (always?) 0x0F for broadcast
            elif raw_bytes[3] & 0x08:
                self.tx_id = raw_bytes[3] & 0x07
                self.rx_id = 0xF1  # made-up to mimic all other protocols
            else:
                untested("11-bit message header from tester (functional or physical)")
                self.tx_id = 0xF1  # made-up to mimic all other protocols
                self.rx_id = raw_bytes[3] & 0x07
        else:
            self.priority = raw_bytes[0]  # usually (always?) 0x18
            self.addr_mode = raw_bytes[1]  # DB = functional, DA = physical
            self.rx_id = raw_bytes[2]  # 0x33 = broadcast (functional)
            self.tx_id = raw_bytes[3]  # 0xF1 = tester ID
        return


class ISO15765Frame(Frame):
    """Represents a frame of the ISO15765 protocol.

    On ISO15765 buses, there is a clear distinction between frames
    (individual packets sent on the bus) and messages (reassembled from
    the frames, sometimes by the interface).

    NOTE: Not all interfaces need to use ISO15765 frames for reassembly,
    since some OBD interfaces internally manage reassembly of ISO15765
    frames into complete messages.  Instead of returning actual frames,
    they return the reassembled, complete message.  Such interfaces should
    call Protocol.create_frame() to create a generic Frame object that
    performs no reassembly.
    
    The default behavior of a ISO15765_4 protocol instance is to use
    this class to represent received frames.

    raw_bytes -- the complete set of raw bytes making up the frame,
        including header and any checksum bytes
    header -- an instance of the appropriate protocol-specific Header
        subclass encapsulating the header bytes
    data_bytes -- the set of data bytes in the frame, excluding header
        and any checksum bytes
    
    assemble_message() -- Return the reassembled bytes given the full
        set of received frames.
    """
    SF = 0x00  # single frame
    FF = 0x10  # first frame of multi-frame message
    CF = 0x20  # consecutive frame(s) of multi-frame message

    def sequence_number(self, last_sn):
        """Return the position of this frame in the sequence, or
        None if there is no specified ordering.
        
        last_sn -- the most recently seen sequence number; this
            is necessary to determine the actual sequence number
            since ISO15765 only uses 4 bits to encode the
            sequence number, and messages may be (much) longer
            than 16 frames
        """
        frame_type = self.data_bytes[0] & 0xF0
        if frame_type == self.SF or frame_type == self.FF: return 0
        if frame_type == self.CF:
            # Frame sequence numbers only specify the low order bits, so compute the
            # full sequence number from the frame number and the last sequence number seen:
            # 1) take the high order bits from the last_sn and low order bits from the frame
            seq = (last_sn & ~0x0F) + (self.data_bytes[0] & 0x0F)
            # 2) if this is more than 7 frames away, we probably just wrapped (e.g.,
            # last=0x0F current=0x01 should mean 0x11, not 0x01)
            if seq < last_sn - 7:
                untested("more than 16 frames in a message")
                seq += 0x10
            return seq
        untested("FC or unknown CAN frame")
        return None # default to no sequence number
    def sequence_length(self):
        """Return the number of frames in the sequence, or None
        if the length is not known.
        
        The length is only known for Single Frame messages or
        for the First Frame in a multi-frame message.
        """
        length = self.data_length()
        if length:
            if length <= 7:
                length = 1  # single frame can hold 7 bytes
            else:
                # 6 bytes in the first frame, 7 bytes in consecutive frames
                length = (length // 7) + 1
        return length
    def data_length(self):
        """Return the number of data bytes contained in the complete,
        reassembled sequence, or None if this frame has no such
        information.
        
        The number of bytes is only known for a Single Frame
        message or the First Frame in a multi-frame message.
        Consecutive frames have no such information.
        """
        frame_type = self.data_bytes[0] & 0xF0
        length = self.data_bytes[0] & 0x0F
        if frame_type == self.SF:
            # Single Frames have a 4-bit length after the frame tyep nibble
            if length > 7: raise VehicleException(message="ISO15765 single frame len > 7", raw=self)
            return length
        if frame_type == self.FF:
            if length: untested("more than 255 bytes in a CAN message")
            # First Frames have a 12-bit length after the frame type nibble
            return (length << 8) + self.data_bytes[1]
        return None  # default to unknown length
    def assemble_message(self, frames):
        """Return the bytes contained in the complete, reassembled
        sequence.

        Reassemble the data contained in the individual frames into
        the list of bytes comprising the complete message, excluding
        any frame headers or footers.
        
        frames -- the list of frames in the sequence
        """
        result = []
        for i, frame in enumerate(frames):
            offset = 1  # skip PCI byte in SF or CF frame
            if i == 0 and len(frames) > 1:
                offset = 2  # skip both PCI bytes in a FF frame
            if frame == None:
                untested("missing frame in CAN message")
                # insert None for each missing byte in a missing frame
                result += [None] * (len(self.data_bytes) - offset)
            else:
                result += frame.data_bytes[offset:]
        return result


# MARK: -

class SAE_J1939(CAN):
    """Represents the SAE J1939 protocol
    
    name -- the human-readable name of the protocol
    baud -- the baud rate used to communicate with the vehicle

    This is currently only used to specify the protocol to be used
    (or supported) by an interface, and is not otherwise implemented.
    """
    def __init__(self, id_length=29, receive_id_length=None, data_length=8, baud=250000):
        """id_length -- 11 or 29 to represent 11-bit or 29-bit headers
            (default 29)
        data_length -- payload size of each frame (default 8 bytes)
        baud -- the baud rate used to communicate with the vehicle
            (default 500K)
        """
        CAN.__init__(self, "SAE_J1939",
                     id_length=id_length,
                     receive_id_length=receive_id_length,
                     data_length=data_length,
                     baud=baud)
        return
    def create_header(self, raw_bytes):
        """Return the appropriate protocol-specific header encapsulating
        the header bytes in the given data
        
        Not implemented.
        """
        raise NotImplementedError()
        return
    def create_frame(self, raw_bytes):
        """Return the appropriate protocol-specific Frame object
        encapsulating the given data and reassembling it into a
        complete message.
        
        Not implemented.
        """
        raise NotImplementedError()
        return
        

# vim: softtabstop=4 shiftwidth=4 expandtab                                     
