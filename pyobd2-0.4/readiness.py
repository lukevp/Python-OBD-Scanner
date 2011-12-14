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
from optparse import OptionParser

import obd
from obd.message import OBDRequest
from obd.util import untested
import obd.util

def check_readiness(r):
    result = "Unknown"

    supported = r.supported_monitors() - r.continuous_monitors
    if len(supported) == 0:
        print "No OBD monitors reported as supported.  Is the engine running?"
    else:
        print r.emissions_status()
        result = "PASS"

        incomplete = r.incomplete_monitors() - r.continuous_monitors
        if (len(incomplete) > 0):
            if (len(incomplete) > 2):
                result = "FAIL"
            else:
                result = "Varies by model year -- check with your state."
            print "%d OBD Monitors are not ready." % len(incomplete)

    print "OBD Readiness Monitor Result:  %s\n" % result
    return


def get_interface():
    usage = "Usage: %prog [--port PORT]"
    parser = OptionParser(usage=usage)
    parser.add_option("-p", "--port", metavar="PORT",
                      help="use the interface attached to PORT")
    options, args = parser.parse_args()

    try:
        interface = obd.interface.create(options.port, "--port")
    except obd.exception.OBDException as e:
        sys.stderr.write(str(e))
        sys.exit(1)
        
    return interface


def query_vehicle(interface):
    interface.open()
    interface.set_protocol(None)
    interface.connect_to_vehicle()

    responses = interface.send_request(OBDRequest(sid=0x01, pid=0x01))

    # Find the response(s) for ECUs that support emissions monitors
    ecus = []
    for r in responses:
        supported = [m for m in r.non_continuous_monitors
                     if m in r.supported_monitors()]
        if len(supported) > 0:
            ecus.append(r)

    # If the engine's off (none support monitors), just pick the first
    if len(ecus) == 0:
        ecus.append(responses[0])

    # Print the readiness status
    for ecu in ecus:
        if len(ecus) > 1:
            untested("multiple ECUs with supported monitors")
            print "ECU 0x%02X:" % response.header.tx_id
        check_readiness(ecu)

    interface.disconnect_from_vehicle()
    interface.close()
    return

def main():
    interface = get_interface()
    query_vehicle(interface)


if __name__ == "__main__":
    main()
