pyOBD-II alpha 0.4
Copyright (c) 2009 Peter J. Creath


OVERVIEW
--------
pyOBD-II (a.k.a. "pyobd2") is a Python library for communicating with
OBD-II vehicles.  Its goal is to make writing programs for vehicle
diagnostics and monitoring vehicle data as easy as possible.  Being
written entirely in Python, pyobd2 is intended to be portable across
many platforms, including Mac OS X, Linux, BSD, and Windows.

While pyobd2 has been extensively tested with a few vehicles, it has
not yet been tested with a wide variety of vehicles.  As a result,
I would greatly appreciate any bug reports, and especially
communication logs from people with vehicles that speak protocols I
haven't been able to test.  See USAGE below for more details on how
to help.

Many thanks to Vitaliy Maksimov at ScanTool.net for his generous and
in-depth support of this project!  pyobd2 wouldn't have been nearly
as robust or well-tested without his help.  ScanTool.net sells and
supports scan tools and other automotive test equipment at
<http://www.scantool.net>.


EXPLANATION
-----------
If you're intimidated by the acronym soup, here is a short explanation
in lay terms:

Recent and future cars and trucks all contain small computers that,
among other things, monitor their exhaust and emissions and report
those data upon state inspection.  They report this information in a
set of common protocols often called "OBD", short for On-Board
Diagnostic.  (The official name for the protocols and their
specifications involves more alphabet soup.)

You can connect your computer to the OBD interface of your vehicle using
a "scan tool", a small device that sits between your computer's serial
(or USB) port and your car's OBD port.

But then you need to talk to the vehicle.  That's where pyobd2 comes
in.  You can issue queries to the vehicle, and pyobd2 will handle the
details, returning the response to you as a Python object, which you
can then inspect and use as you like.  The goal is to make this very
easy, so that client programs can focus on powerful features and
intuitive user interface without having to worry about the low-level
plumbing.

pyobd2 was written from scratch in 2009 by Peter J. Creath and is
unrelated to the apparently abandoned "pyobd" by Donour Sizemore (last
updated in 2004).  I apologize for the confusing naming -- there are
only so many ways to express "Python OBD library".


REQUIREMENTS
------------
- ELM327-compatible scan tool:
  pyobd2 currently supports only ELM327-compatible scan tools.  You will
  need such a scan tool in order to connect your computer with your car. 

  You can purchase a scan tool from <http://www.scantool.net/scan-tools/>.

- pySerial
  pyobd2 relies on pySerial to communicate with scan tools.  It has been
  tested with pySerial 2.4 and Python 2.6, but should generally work with
  other versions as well.

  NOTE: pySerial 2.5rc1 is known not to work on Darwin.


USAGE
-----
In its present state, pyobd2 is largely a library for further development.
There are two command-line programs of interest:

readiness.py -- queries a vehicle for its emissions inspection readiness;
    Checking for readiness requires that the vehicle's engine be running.
    Then run this script to see which internal monitors are ready for testing.

record-all.py -- runs through all of the regression tests and records the
    communication sessions, packaging them up into "recorded-data.zip".
    To assist in the debugging and development of pyobd2, run this script
    and please send the resulting .zip file.

The above two programs are reasonably useful sample code for using the
pyobd2 library.  The general outline of usage is:

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



KNOWN LIMITATIONS
-----------------
These limitations are not necessarily intended to be permanent; they are
simply the known limitations as of writing.  If there's a limitation here
that you'd like addressed, please don't hesitate to contact me.

* Only ELM327 and compatible interfaces are currently supported.  This
  includes the ElmScan 5, OBDLink, and OBDLink CI from ScanTool.net.

* Serial port enumeration only works on Darwin (Mac OS X), and maybe BSD.
  An interface may still be created manually on other platforms by explicitly
  passing a known serial port.

* Setting headers (to direct requests to specific ECUs) is not yet supported,
  though it is still possible to ask the interface to set the header manually.

* Handling of group requests (ISO 15765 only) is not yet implemented, though
  it should still be possible to send any arbitrary request to the interface.

* Due to a bug in pySerial 2.4, 230Kbps is the highest baud rate supported
  on Darwin, and probably other POSIX platforms.

* There is no API (yet) for passively monitoring the bus, though it should
  still be possible to ask the interface to begin monitoring.

* There's not much documentation yet.

* The API is not completely stable yet.

* Reading from the serial port may wait slightly longer than the specified
  timeout, up to 0.01 seconds by default.  If necessary, this can be adjusted
  changing the value of obd.serialport.SerialPort.MAX_READ_OVERRUN.

* Many OBD messages are not yet extracted into structured Response objects;
  they are only encapsulated in generic objects that contain the raw data.
