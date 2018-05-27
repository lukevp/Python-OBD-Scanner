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
Base module for pyOBD-II (a.k.a. "pyobd2"), a library for communicating
with OBD-II vehicles.  Its goal is to make writing programs for vehicle
diagnostics and monitoring vehicle data as easy as possible.

Sample usage:

    import obd
    import obd.message.OBDRequest

    # Find the scan tools attached to the computer and pick one
    interfaces = obd.interface.enumerate()
    interface = interfaces[0]

    # Open the connection with the vehicle
    interface.open()
    interface.set_protocol(None)
    interface.connect_to_vehicle()

    # Communicate with the vehicle
    request = obd.message.OBDRequest(sid=0x01, pid=0x00)
    responses = interface.send_request(request)

    # Close the connection
    interface.disconnect_from_vehicle()
    interface.close()

See obd.interface, obd.message, and obd.exception for further details.
"""

__all__ = ["interface", "exception", "message", "util", "protocol", "serialport"]

import obd.interface
import obd.exception
import obd.message

if __name__ == "__main__":
    pass

# vim: softtabstop=4 shiftwidth=4 expandtab                                     
