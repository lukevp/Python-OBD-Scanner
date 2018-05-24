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
import glob
import os
import subprocess
import zipfile

import obd

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

def record_all_tests(port):
    # run all the tests in record mode
    os.chdir("test")
    for test in glob.glob("test_*.py"):
        sys.stderr.write("=== Recording %s ===\n" % test)
        test = os.path.join(".", test)
        #command = [test, "--record", "--port=%s" % port]
        #print " ".join(command)
        command = "%s --record --port=%s" % (test, port)
        subprocess.check_call(command, shell=True)
    os.chdir("..")

    # create a .zip archive of the recorded data
    try:
        z = zipfile.ZipFile("recorded-data.zip", "w", zipfile.ZIP_DEFLATED)
    except RuntimeError:
        z = zipfile.ZipFile("recorded-data.zip", "w")
    textfiles = os.path.join("test", "*.txt")
    for filepath in glob.glob(textfiles):
        filename = os.path.split(filepath)[1]
        z.write(filepath, filename)
    z.close()

    return

def main():
    interface = get_interface()
    #class Foo(object):
    #    pass
    #interface = Foo()
    #interface.identifier="/dev/test"
    record_all_tests(interface.identifier)


if __name__ == "__main__":
    main()
