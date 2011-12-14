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

import sys
import glob
import os
import traceback
from optparse import OptionParser

sys.path.append("..")
import obd
from obd.serialport import SerialPortPlayback, SerialPortRecorder

verbose = False

def create_test_elm(filename=None, mimic_timing=False):
    """Create an ELM interface instance for use with recording or
    replaying a test session"""
    port = _create_test_port(filename, mimic_timing)
    return obd.interface.elm.create(port)

def create_test_port(filename=None, mimic_timing=False):
    """Create a port instance for recording or replaying
    a test session"""
    return _create_test_port(filename, mimic_timing)

def _create_test_port(filename, mimic_timing):
    # Find the default (local) file for this test
    module = _get_caller_module_name(offset=2)
    default_filename = module + ".txt"

    # If we're being run as part of a full regression test,
    if "py.test" in sys.modules:
        if filename is None:
            filename = default_filename
            if not os.path.exists(filename):
                # Don't consider the lack of a local file an error
                import py.test
                py.test.skip("no local data for %s" % module)
        # Ignore any command-line options and just do playback
        serial_port = SerialPortPlayback(filename, mimic_timing=mimic_timing)
        return serial_port

    options, args = _get_test_arguments()
    if filename is None:
        if len(args) > 0:
            filename = args[0]
        else:
            filename = default_filename

    global verbose
    verbose = options.verbose
    
    if (options.record):
        sys.stderr.write("[Recording to %s from %s]\n" % (filename, options.port))
        serial_port = SerialPortRecorder(options.port, filename)
    else:
        serial_port = SerialPortPlayback(filename, mimic_timing=mimic_timing)

    return serial_port

def _get_caller_module_name(offset=0):
    caller = traceback.extract_stack(limit=2+offset)[0]
    filename = caller[0]
    filename = os.path.split(filename)[1]
    filename = os.path.splitext(filename)[0]
    return filename

def _get_test_arguments():
    default_port = "/dev/cu.usbserial-ST*"

    usage = "Usage: %prog [--record [--port PORT]] [session file]"
    parser = OptionParser(usage=usage)
    parser.add_option("-r", "--record",
                      action="store_true", default=False,
                      help="record new data for this test")
    parser.add_option("-p", "--port", metavar="PORT",
                      help="if recording, use the interface" +
                           "attached to PORT (defaults to %s)" % default_port)
    parser.add_option("-v", "--verbose",
                      action="store_true", default=False,
                      help="produce more output")
    options, args = parser.parse_args()

    if options.record and options.port == None:
        try:
            options.port = glob.glob(default_port)[0]
        except IndexError:
            parser.print_usage(sys.stderr)
            sys.stderr.write("Unable to find default port; please specify one explicitly.\n")
            sys.exit(2)

    return options, args

def unexpected_error(e):
    """Log unexpected errors but continue to record (or playback)
    when running a test interactively.  Flag the error if being
    run as part of a regression test.
    """
    if "py.test" in sys.modules:
        raise e
    traceback.print_exc(file=sys.stderr)
    return


protocols = ["iso9141", "iso15765_11bit", "iso15765_29bit"]
def define_protocol_tests(globals=globals(), protocols=protocols):
    """Dynamically create test_* functions for use by py.test
    
    A separate function is defined for each protocol and for
    any local test data.  These functions call do_test() on
    each session file associated with this test.
    
    globals -- the global dict indicating the scope in which
        the functions should be defined; typically the caller
        should pass its own globals()
    protocols -- the list of protocols to test; defaults to
        all defined protocols
    """
    module = _get_caller_module_name(offset=1)
    exec "import testharness" in globals
    exec """def test_current(): do_test()""" in globals
    
    for protocol in protocols:
        code = """def test_%s():
            testharness._do_protocol_test("%s", "%s", do_test)""" %\
            (protocol, protocol, module)
        exec code in globals

    return

def _do_protocol_test(protocol, module, test_fn):
    pattern = os.path.join(protocol, module) + "*.txt"
    tests = glob.glob(pattern)

    if not tests:
        try:
            import py.test
            py.test.skip("no %s data for %s" % (protocol, module))
        except ImportError:
            pass

    for test_file in tests:
        test_fn(test_file)
    
    return


def create_obd_message_from_ascii(ascii):
    """Create an OBD message object from an ASCII representation"""
    raw_bytes = convert_ascii_to_bytes(ascii)
    return create_obd_message(raw_bytes)

def convert_ascii_to_bytes(ascii):
    """Convert a string of hex digits into a list of bytes (integers)"""
    raw = []
    ascii = ascii.replace(" ", "")
    for i in range(0, len(ascii), 2):
        raw.append(int(ascii[i:i+2], 16))
    return raw

def create_obd_message(raw_bytes):
    """Create and OBD message object from a list of bytes"""
    # Prepend ISO15765 header for ECU#1
    prefix = [0x18, 0xDA, 0xF1, 0x10]
    raw_bytes = prefix + raw_bytes
    # Convert the raw data to a frame that requires no reassembly
    protocol = obd.protocol.ISO15765_4()
    frame = obd.protocol.Protocol.create_frame(protocol, raw_bytes)
    # Create a bus message from the frame
    header = frame.header
    data = frame.data_bytes
    frames = [frame]
    bus_message = obd.message.BusMessage(header, data, frames)
    # Create the OBD message from the bus message
    message = obd.message.create(bus_message)
    return message


# vim: softtabstop=4 shiftwidth=4 expandtab
