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

"""Implementation of base Interface class"""

import copy
import Queue
import time

import obd.message
import obd.protocol
from obd.util import info, debug, untested

class Interface(object):
    """Base class representing the OBD-II interface attached to the computer

    Basic usage:

        interface.open()
        interface.connect_to_vehicle()

        responses = interface.send_request(request)

        interface.disconnect_from_vehicle()
        interface.close()
    """

    OBD_REQUEST_TIMEOUT = 9.9
    ECU_TIMEOUT = 5.0

    def __init__(self, identifier, name, callback=None):
        """
        identifier -- an identifier that persistently specifies
            the interface; this might be the serial port to which
            the interface is attached, or some other identifier
            (such as a USB serial number)
        name -- the descriptive name of the interface
        callback -- a function to be called with status updates during
            long operations (such as connecting to a vehicle); the one
            argument sent to the callback is a string containing a status
            message
        
        The callback may also be set (or changed) later, via
        set_status_callback().
        """
        self._current_status = None
        self._status_callback_fn = callback
        self._token = None
        self._frames_received = {}
        self._complete_messages = Queue.Queue(0)
        self.identifier = identifier
        self.name = name
        return

    def __str__(self):
        return "%s (%s)" % (self.identifier, self.name)

    def _status_callback(self, str):
        """Send a status message to the current callback function
        (if any).
        
        This is the preferred way to send callbacks, since it
        correctly handles a null callback and suppresses any
        duplicate messages.

        str -- the message to send
        """
        if self._current_status == str: return
        self._current_status = str
        info("status: " + str)
        if (self._status_callback_fn):
            self._status_callback_fn(str)
        return

    def set_status_callback(self, fn):
        """Set the callback function to be called with status updates
        during long operations (such as connecting to a vehicle).
        
        fn -- the callback function, or None to disable status updates;
            the one argument sent to the callback is a string
            containing a status message
        """
        self._status_callback_fn = fn
        return

    def _verify_token(self, token):
        """Raise an exception if the given token does not match the value
        specified by the previous ResetRequiresConfirmation exception.
        
        All interface implementations should call this at the lowest possible
        level, immediately prior to sending a SID $04 request on the wire."""
        if not token or token != self._token:
            e = obd.exception.ResetRequiresConfirmation()
            self._token = e.token
            raise e
        return

    def open(self):
        """Configure the interface (scan tool) for use.
        
        This does not initiate a connection with the vehicle; it simply
        opens the connection between the computer and the interface.
        See connect_to_vehicle() for comparison.
        """
        raise NotImplementedError()
        return
    
    _supported_protocols = []

    def get_supported_protocols(self):
        """Return the list of supported protocols for this interface.
        
        Each item in the list is a copy of a Protocol object (or None).
        """
        return [copy.copy(p) for p in self._supported_protocols]
    supported_protocols = property(get_supported_protocols,
                                   doc="The list of supported protocols for this interface")

    def set_protocol(self, protocol):
        """Select the protocol to use for communicating with the vehicle.
        This will disconnect any communication session with the vehicle
        already in progress.
        
        protocol -- the protocol to use, or None for automatic selection
            by the interface (if supported)
        """
        raise NotImplementedError()
        return

    def get_protocol(self):
        """Return the current protocol being used in communication with the
        vehicle.

        Raises an exception if not connected with a vehicle.
        """
        raise NotImplementedError()
        return
        
    def connect_to_vehicle(self):
        """Initiate a communication session with the vehicle's ECU
        and return the session protocol.

        This may take several seconds, particularly if automatic protocol
        detection is being used.  Where possible, the specified callback
        function will be used to provide status updates.
        
        Raises an exception if unable to establish the connection.
        """
        raise NotImplementedError()
        return

    def disconnect_from_vehicle(self):
        """Terminate an existing communication session with a
        vehicle.
        
        Raises an exception if there is no active session.
        """
        raise NotImplementedError()
        return

    def _send_obd_message(self, message, header=None, token=None):
        """Transmit an OBD message on the bus.
        
        message -- the message bytes to transmit
        header -- the header used to address the message (or None
            for broadcast)
        token -- the token required to send a Reset message
            (if applicable)
        """
        # All interface implementations should call _verify_token() at the
        # lowest possible level, immediately prior to sending a SID $04
        # request on the wire.
        raise NotImplementedError()
        return

    response_type = "obd_responses"

    def send_request(self, request, header=None, token=None, response_type="default"):
        """Send a request to the vehicle over the OBD-II bus and return
        the response received.
        
        By default, this function will return a list of the received
        OBD messages, each represented as the appropriate Response
        subclass.  See obd.message for Response details and the
        response_type argument below for alternatives.
        
        An exception will be raised if there were any data errors
        in the response.
        
        request -- an instance of a Request subclass encapsulating the
            data to send (see obd.message.OBDRequest and
            obd.message.RawRequest)
        header -- an instance of a Header subclass used to address the
            message (or None, the default, for broadcast)
        token -- the token required to send a Reset message
            (if applicable)
        response_type -- how the response to this request should be
            encapsulated
        
        The response_type default is to use the interface.response_type
        setting, which in turn defaults to "obd_responses".  Valid settings
        for response_type are:
        
            "obd_responses" -- return a list of received OBD messages, each
                message represented as the approprate Response subclass
                (default)
            "bus_messages" -- return a list of reassembled bus messages,
                each message represented as a BusMessage instance
            "raw_frames" -- return a list of each frame received, each frame
                represented as a list of raw bytes
            function pointer -- called with the list of raw frames to allow
                for any other processing or transformation
        
        See obd.message.base.BusMessage and obd.message.base.Message for
        further details on the distinction between these options.
        """
        assert self.interface_configured
        assert self.connected_to_vehicle
        if response_type == "default":
            response_type = self.response_type
        message = request.message(self.vehicle_protocol)
        raw_frames = self._send_obd_message(message, header, token)            
        if response_type == "raw_frames":
            result = self._return_raw_frames(raw_frames)
        elif response_type == "bus_messages":
            result = self._return_bus_messages(raw_frames)
        elif response_type == "obd_responses":
            result = self._return_obd_responses(raw_frames)
        else:
            # let clients provide their own custom handler via function
            result = response_type(self, raw_frames)
        return result


    def _return_raw_frames(self, raw_frames):
        """Return the list of raw frames untouched, but raise an
        exception if there were any data errors.
        """
        for f in raw_frames:
            if None in f:
                untested("frames with data errors")
                raise DataError(raw=raw_frame)
        return raw_frames

    def _return_bus_messages(self, raw_frames):
        """Reassemble a list of raw frames into complete BusMessages and
        raise an exception if there were any data errors; otherwise
        return the list of bus messages.
        """
        bus_messages = self._process_obd_response(raw_frames)
        for r in bus_messages:
            if r.incomplete:
                untested("messages with bad frames")
                raise DataError(raw=bus_messages)
        return bus_messages

    def _return_obd_responses(self, raw_frames):
        """Reassemble a list of raw frames into complete OBD responses,
        each represented as the appropriate Response subclass, and
        raise an exception if there were any data errors.  Otherwise
        return the list of OBD responses.
        """
        bus_messages = self._process_obd_response(raw_frames)
        obd_messages = [obd.message.create(m) for m in bus_messages]
        for r in obd_messages:
            if r.incomplete:
                untested("messages with bad frames")
                raise DataError(raw=obd_messages)
        return obd_messages

    def _process_obd_response(self, raw_frames):
        """Reassemble a list of raw frames into complete BusMessages,
        assuming that the list of raw frames constitutes a complete
        response.
        """
        # When we get an OBD response from the interface, we assume that it's
        # basically complete, having taken into account any relevant timeouts
        for frame in raw_frames:
            self._received_obd_frame(frame)
        self._flush_frames()
        result = []
        try:
            while True:
                bus_message = self._complete_messages.get(False)
                result.append(bus_message)
        except Queue.Empty as e:
            # The queue is exhausted, which just means we're done.
            pass

        debug([str(r) for r in result])
        return result

    def _parse_frame(self, raw_frame):
        """Return an instance of the appropriate Frame subclass given
        the current protocol.

        Interfaces that wish to skip multi-frame reassembly (such as
        interfaces that reassemble CAN messages themselves) should
        override this function to call Protocol.create_frame()
        for such messages.
        """
        return self.vehicle_protocol.create_frame(raw_frame)

    def _received_obd_frame(self, raw_frame):
        """Add a received frame to the set of currently pending
        messages.  If this frame completes a message, post the
        message to the _complete_messages Queue.
        
        Note that this function may not be able to determine
        whether a message is complete.  See _flush_frames()
        for resolution.
        """
        frame = self._parse_frame(raw_frame)
        key = frame.sequence_key()

        # Get the set of incomplete frames for the given transmitter and receiver
        try:
            frames, last_sequence_number, sequence_length = self._frames_received[key]
        except KeyError as e:
            frames, last_sequence_number, sequence_length = [], 0, None
            self._frames_received[key] = [frames, last_sequence_number, sequence_length]

        # Compute the current frame's sequence number
        sequence_number = frame.sequence_number(last_sequence_number)

        # Determine the number of frames needed to complete this response
        if sequence_length is None:
            sequence_length = frame.sequence_length()
        frames_needed = sequence_length
        if not frames_needed:
            # If we can't tell how many frames are needed for this message, we know
            # the response needs at least enough frames for this one
            if sequence_number is None:
                frames_needed = 0
            else:
                frames_needed = sequence_number + 1

        # Make sure there's room in the list of frames
        if len(frames) < frames_needed:
            frames_needed -= len(frames)
            frames.extend([None] * frames_needed)

        # Save the current frame
        if sequence_number is not None:
            frames[sequence_number] = frame
        else:
            # Store unordered frames in the first available slot
            try:
                frames[frames.index(None)] = frame
            except ValueError:
                frames.append(frame)

        # When all the needed frames are received,
        sequence_length_known = (sequence_length is not None)
        if sequence_length_known and None not in frames:
            # Post the completed message and clear the (now) completed frames
            data = frames[0].assemble_message(frames)
            bus_message = obd.message.BusMessage(frame.header, data, frames)
            self._complete_messages.put(bus_message, False)
            del self._frames_received[key]
        else:
            # Save the most recent sequence number seen
            self._frames_received[key] = [frames, sequence_number, sequence_length]
        return
    
    def _flush_frames(self):
        """Flush any pending messages and post them to the
        _complete_messages Queue.
        
        Messages may be pending because they are incomplete
        (e.g. a frame is missing) or because _received_obd_frame()
        was unable to determine that they were complete.
        
        This function should be called when it is determined
        that a response is complete.  In the case of discrete
        request/response transactions, this is often trivial.
        In the case of bus monitoring, more complex logic
        must be employed to determine when frames should be
        flushed.
        """
        try:
            # Iterate over all pending messages
            for frames, sequence_number, sequence_length in self._frames_received.values():
                # If the message is pending because it is incomplete
                if None in frames:
                    untested("flushing incomplete messages")
                    # Find the first received (non-None) frame, in case we missed the
                    # first frame(s).  The assertions check for bugs in received_frame().
                    for first_received in frames:
                        if first_received != None: break
                    else:
                        assert False, "message with no frames received"
                else:
                    # If the sequence length was known, the message should have been
                    # flushed as soon as it was complete.
                    sequence_length_known = (sequence_length is not None)
                    assert not sequence_length_known, "message not flushed upon completion"
                    first_received = frames[0]
                # Post the pending message
                header = first_received.header
                data = first_received.assemble_message(frames)
                bus_message = obd.message.BusMessage(header, data, frames)
                self._complete_messages.put(bus_message, False)
        finally:
            # Clear the pending messages
            self._frames_received = {}
        return
        
    def close(self):
        """Release the interface (scan tool) from use.  This may
        or may not disconnect the communication session between
        the interface and the vehicle, depending on implementation.
        """
        raise NotImplementedError()
        return

    def reset(self, quick=True):
        """Reset the interface (scan tool)
        
        quick -- peform a quick reset (if supported), otherwise perform
            a slower, full reset
        """
        raise NotImplementedError()
        return
        
    def search_for_protocol(self):
        """Perform a robust search for the vehicle's protocol and
        initiate a communication session with the vehicle's ECU,
        returning the session protocol if successful.

        This may take many seconds, as some protocols require a
        delay after a failed test.  To mitigate this, the specified
        callback function will be called before trying each
        supported protocol.
        
        Raises an exception if unable to determine the protocol
        and establish the connection.
        """
        search_order = [
            [obd.protocol.PWM(), 1.0],
            [obd.protocol.VPW(), 0.0],
            [obd.protocol.ISO9141_2(), 5.0],
            [obd.protocol.ISO14230_4("5BAUD"), 5.0],
            [obd.protocol.ISO14230_4("FAST"), 0.0],
            [obd.protocol.ISO15765_4(id_length=11, baud=500000), 0.0],
            [obd.protocol.ISO15765_4(id_length=29, baud=500000), 0.0],
            [obd.protocol.ISO15765_4(id_length=11, baud=250000), 0.0],
            [obd.protocol.ISO15765_4(id_length=29, baud=250000), 0.0],
            ]
        supported_protocols = self.get_supported_protocols()

        for protocol, delay in search_order:
            if protocol not in supported_protocols:
                continue
            self._status_callback("Trying %s protocol..." % str(protocol))
            self.set_protocol(protocol)
            try:
                self.connect_to_vehicle()
                break
            except obd.exception.ConnectionError as e:
                debug("%s, delaying %f" % (str(e), delay))
                time.sleep(delay)
        else:
            raise obd.exception.ProtocolError("unable to determine vehicle protocol")

        return self.get_protocol()

# vim: softtabstop=4 shiftwidth=4 expandtab                                     

