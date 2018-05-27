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

import time
DELAY = 0.01

from testharness import create_test_elm, unexpected_error, define_protocol_tests

import obd
import obd.interface.elm
import obd.util
from obd.message import OBDRequest

def get_supported_pids(elm, sid, start_pid):
    # default to all in case the support query fails for some reason
    supported_pids = range(start_pid + 1, start_pid + 1 + 0x20)

    try:
        responses = elm.send_request(OBDRequest(sid=sid, pid=start_pid))
        support = responses[0]
        supported_pids = support.supported_pids
        pids = ",".join(["$%02X" % pid for pid in supported_pids])
        print "supported pids for sid=$%02X pid=$%02X: [%s]" % (sid, start_pid, pids)
        obd.util.debug(supported_pids)
    except obd.exception.DataError as e:
        print "unable to determine PID support for sid=$%02X pid=$%02X, assuming none supported" % (sid, start_pid)
        supported_pids = []
        obd.util.debug(supported_pids)
    except Exception as e:
        unexpected_error(e)

    return supported_pids


def read_all_supported_pids(elm, sid):

    for pid_support in range(0x00, 0x100, 0x20):
        time.sleep(DELAY)
        supported_pids = get_supported_pids(elm, sid, pid_support)

        # issue individual requests
        for pid in supported_pids:
            if pid == pid_support + 0x20:
                # fetched next time through outer loop
                break

            try:
                time.sleep(DELAY)
                responses = elm.send_request(OBDRequest(sid=sid, pid=pid))
                #print "got response for sid=$%02X pid=$%02X" % (sid, pid)
            except obd.exception.DataError:
                print "no response to sid=$%02X pid=$%02X" % (sid, pid)
                continue
            except Exception as e:
                unexpected_error(e)
                continue

            for r in responses:
                print "%s: %s" % (r.bus_message.header, str(r))

        if pid_support + 0x20 not in supported_pids:
            # stop if no higher pid_support queries are supported
            break
    return

def read_all_supported_tests(elm, sid):
    read_all_supported_pids(elm, sid)
    return

def read_dtcs(elm, sid):
    try:
        responses = elm.send_request(OBDRequest(sid=sid))
        for r in responses:
            print "%s: %s" % (r.bus_message.header, str(r))
    except obd.exception.DataError:
        pass
    except Exception as e:
        unexpected_error(e)
    return


define_protocol_tests(globals())


def do_test(filename=None):
    elm = create_test_elm(filename)
    try:
        elm.open()
        elm.set_protocol(None)
        elm.connect_to_vehicle()
    except Exception as e:
        unexpected_error(e)
        # if the connection fails, everything else will too
        return

    read_all_supported_pids(elm, 0x01)

    # Awaiting implementation of Service $02
    # frames = elm.get_frame_count()
    # for f in range(0, frames):
    #     elm.get_data(all_values, frame=f)

    read_dtcs(elm, 0x03)

    # skip Service $04 (resets DTCs)

    # Awaiting implementation of Service $05
    # O2 sensor locations appended to request
    # (legacy protocols only; not supported by ISO 15765)

    # Awaiting implementation of Service $06
    # legacy responses have a filler byte before the pid-supported
    # data
    read_all_supported_tests(elm, 0x06)

    read_dtcs(elm, 0x07)

    # Skip Service $08 (controls a physical test)

    read_all_supported_pids(elm, 0x09)

    read_dtcs(elm, 0x0A)
    return


if __name__ == "__main__":
    do_test()

# vim: softtabstop=4 shiftwidth=4 expandtab

