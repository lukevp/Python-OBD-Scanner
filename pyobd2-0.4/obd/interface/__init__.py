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

from obd.exception import OBDException, InterfaceNotFound
from obd.util import untested

"""
This submodule manages communication with a vehicle over the OBD
bus via Interface and its subclasses, wich represent an OBD-II
interface ("scan tool") attached to the computer.

The easiest way to create an interface instance is via:

enumerate() -- returns a list of all OBD-II interfaces detected; each
    interface is represented by an instance of the appropriate
    subclass of Interface.

create(identifier) -- creates an instance of the appropriate
    Interface subclass representing the interface specified by
    the given identifier.

See the obd.interface.base.Interface class for details on
communicating with a vehicle.
"""

_interface_classes = []

def register_interface_class(class_):
    """Register an Interface subclass for enumeration."""
    global _interface_classes
    _interface_classes.append(class_)
    return

def enumerate(callback=None):
    """Return a list of all detected OBD-II interfaces.
    
    Each interface is represented by an instance of the appropriate
    Interface subclass."""
    interfaces = []
    for class_ in _interface_classes:
        interfaces.extend(class_.enumerate(callback))
    return interfaces


def create(identifier, argument_name=""):
    """Return the interface specified by the given identifier,
    raising an exception if the interface cannot be created.

    identifier -- the identifier specifying the desired interface;
        this might be the serial port to which the interface is
        attached, or some other identifier (such as a USB serial
        number) used to specify the desired interface.
    argument_name -- text returned in exception messages
        explaining how to specify the identifier, e.g. via
        a "--port" command-line option
        
    If identifier is None, try to detect the interface automatically.
    a) If enumeration is not supported, this will raise an OBDException.
    b) If more than one interface is detected, this will raise
        a ValueError exception listing the detected interfaces
    c) If no interfaces are detected, this will raise an
        InterfaceNotFound exception.
    """
    if identifier is not None:
        for class_ in _interface_classes:
            try:
                interface = class_.create(identifier)
                break
            except:
                pass
        else:
            message = "Unable to connect to scanner at %s; " % identifier
            message += "is it connected and powered?\n"
            raise InterfaceNotFound(message)
    else:
        if argument_name:
            select = " via %s" % argument_name
        else:
            untested("no argument name")
            select = ""
        select = "Please select an interface to use" + select
        try:
            interfaces = obd.interface.enumerate()
        except OBDException as e:
            untested("enumeration not supported")
            message = "%s.\n%s.\n" % (str(e), select)
            raise OBDException(message)
        if len(interfaces) < 1:
            message = "No scanners found; is one connected and powered?\n"
            raise InterfaceNotFound(message)
        if len(interfaces) > 1:
            untested("multiple interfaces")
            message = "%s:\n" % select
            for interface in interfaces:
                message += "  %s\n" % str(interface)
            raise ValueError(message)
        interface = interfaces[0]

    return interface

      
__all__ = ["enumerate", "create", "register_interface_class"]

# Register the specific classes
import obd.interface.elm

# vim: softtabstop=4 shiftwidth=4 expandtab                                     
