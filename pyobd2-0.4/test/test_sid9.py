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

from testharness import create_test_elm, define_protocol_tests
from testharness import create_obd_message_from_ascii

_sample_data = {
    "49 02 01 31 47 31 4A 43 35 34 34 34 52 37 32 35 32 33 36 37": "VIN=1G1JC5444R7252367",
    "49 04 01 4A 4D 42 2A 33 36 37 36 31 35 30 30 00 00 00 00 00": "CALID=JMB*36761500",
    "49 06 01 17 91 BC 82": "CVN=1791BC82",
    "49 08 10 03 40 13 83 01 84 03 40 00 00 00 00 02 08 03 40 00 00 00 00 0E 2F 03 40 00 00 00 00 00 DA 01 20": """OBDCOND=832 counts
IGNCNTR=4995 counts
CATCOMP1=388 counts
CATCOND1=832 counts
CATCOMP2=0 counts
CATCOND2=0 counts
O2SCOMP1=520 counts
O2SCOND1=832 counts
O2SCOMP2=0 counts
O2SCOND2=0 counts
EGRCOMP=3631 counts
EGRCOND=832 counts
AIRCOMP=0 counts
AIRCOND=0 counts
EVAPCOMP=218 counts
EVAPCOND=288 counts""",
    "49 0A 01 45 43 55 31 2D 45 6E 67 69 6E 65 43 6F 6E 74 72 6F 6C 00 00 00 00 00 00": "ECU=ECU1\nECUNAME=EngineControl",
    }

def test_sid09_output():
    for ascii, output in _sample_data.items():
        m = create_obd_message_from_ascii(ascii)
        if str(m) != output:
            print repr(str(m))
            print repr(output)
        assert str(m) == output
    return


if __name__ == "__main__":
    test_sid09_output()

# vim: softtabstop=4 shiftwidth=4 expandtab

