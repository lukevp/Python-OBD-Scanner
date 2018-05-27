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

from testharness import create_test_elm, unexpected_error, define_protocol_tests
from testharness import create_obd_message_from_ascii
from readiness import query_vehicle
import obd.exception

define_protocol_tests(globals())

def do_test(filename=None):
    elm = create_test_elm(filename)
    try:
        query_vehicle(elm)
    except obd.exception.ConnectionError as e:
        unexpected_error(e)
    return

_sample_readiness_data = {
    # Engine off (no tests supported)
    "41 01 00 04 00 00": """Catalyst Monitor                         Not Supported
Catalyst Heater Monitor                  Not Supported
Evaporative System Monitor               Not Supported
Secondary Air System Monitor             Not Supported
A/C System Monitor                       Not Supported
O2 Sensor Monitor                        Not Supported
O2 Sensor Heater Monitor                 Not Supported
Exhaust Gas Recirculation (EGR) Monitor  Not Supported
""",
    # Pass (all tests ready)
    "41 01 00 07 65 00": """Catalyst Monitor                         Ready
Catalyst Heater Monitor                  Not Supported
Evaporative System Monitor               Ready
Secondary Air System Monitor             Not Supported
A/C System Monitor                       Not Supported
O2 Sensor Monitor                        Ready
O2 Sensor Heater Monitor                 Ready
Exhaust Gas Recirculation (EGR) Monitor  Not Supported
""",
    # Fail (3 tests not read)
    "41 01 00 07 65 25": """Catalyst Monitor                         Not Ready
Catalyst Heater Monitor                  Not Supported
Evaporative System Monitor               Not Ready
Secondary Air System Monitor             Not Supported
A/C System Monitor                       Not Supported
O2 Sensor Monitor                        Not Ready
O2 Sensor Heater Monitor                 Ready
Exhaust Gas Recirculation (EGR) Monitor  Not Supported
""",
    # Marginal (1 test not ready)
    "41 01 00 07 65 01": """Catalyst Monitor                         Not Ready
Catalyst Heater Monitor                  Not Supported
Evaporative System Monitor               Ready
Secondary Air System Monitor             Not Supported
A/C System Monitor                       Not Supported
O2 Sensor Monitor                        Ready
O2 Sensor Heater Monitor                 Ready
Exhaust Gas Recirculation (EGR) Monitor  Not Supported
""",
    }

def test_emissions_status():
    for ascii, output in _sample_readiness_data.items():
        m = create_obd_message_from_ascii(ascii)
        assert m.emissions_status() == output
    return

if __name__ == "__main__":
    do_test()
    test_emissions_status()

# vim: softtabstop=4 shiftwidth=4 expandtab

