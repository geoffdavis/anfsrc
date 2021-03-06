"""Utilities for poc2mongo."""
from logging import getLogger
import os

from anf.logutil import fullname
import antelope.Pkt as Pkt
import antelope.stock as stock

MAX_EXTRACT_ERRORS = 10

logger = getLogger(__name__)


class stateFile:
    """Track the state of the ORB read. Save value of pktid in file.

    TODO: consolidate this into the main anf module
    """

    def __init__(self, filename=False, start="oldest"):
        """Initialize the stateFile.

        Args:
            filename (string or False): name of the statefile. If False, don't track state.
            start (string or int): Antelope orb position to start at.

        """

        self.logging = getLogger(fullname(self))

        self.logging.debug("stateFile.init()")

        self.filename = filename
        self.packet = start
        self.time = 0
        self.strtime = "n/a"
        self.latency = "n/a"
        self.pid = "PID %s" % os.getpid()

        if not filename:
            return

        self.directory, self.filename = os.path.split(filename)

        if self.directory and not os.path.isdir(self.directory):
            os.makedirs(self.directory)

        self.file = os.path.join(self.directory, self.filename)

        self.logging.debug("Open file for STATE tracking [%s]" % self.file)
        if os.path.isfile(self.file):
            self.open_file("r+")
            self.read_file()
        else:
            self.open_file("w+")

        if not os.path.isfile(self.file):
            raise PocException("Cannot create STATE file %s" % self.file)

    def last_packet(self):
        """Retrieve the last orb packet."""
        self.logging.info("last pckt:%s" % self.packet)
        return self.packet

    def last_time(self):
        """Retrieve the last time data was read."""
        self.logging.info("last time:%s" % self.time)
        return self.time

    def read_file(self):
        """Read the statefile."""
        self.pointer.seek(0)

        try:
            temp = self.pointer.read().split("\n")
            self.logging.info("Previous STATE file %s" % self.file)
            self.logging.info(temp)

            self.packet = int(float(temp[0]))
            self.time = float(temp[1])
            self.strtime = temp[2]
            self.latency = temp[3]

            self.logging.info(
                "Previous - %s PCKT:%s TIME:%s LATENCY:%s"
                % (self.pid, self.packet, self.time, self.latency)
            )

            if not float(self.packet):
                raise
        except Exception:
            self.logging.warning(
                "Cannot find previous state on STATE file [%s]" % self.file
            )

    def set(self, pckt, time):
        """Store state in the stateFile."""
        if not self.filename:
            return

        self.packet = pckt
        self.time = time
        self.strtime = stock.strlocalydtime(time).strip()
        self.latency = stock.strtdelta(stock.now() - time).strip()

        # self.logging.debug( 'Orb latency: %s' % self.latency )

        try:
            self.pointer.seek(0)
            self.pointer.write(
                "%s\n%s\n%s\n%s\n%s\n"
                % (self.packet, self.time, self.strtime, self.latency, self.pid)
            )
        except Exception as e:
            raise PocException(
                "Problems while writing to state file: %s %s" % (self.file, e)
            )

    def open_file(self, mode):
        """Open stateFile."""
        try:
            self.pointer = open(self.file, mode)
        except Exception as e:
            raise PocException(
                "Problems while opening state file: %s %s" % (self.file, e)
            )


class PocException(Exception):
    """Base class for exceptions raised by this module."""

    pass


class NoOrbDataException(PocException):
    """No data was found matching the select or reject criteria."""


class OrbSelectException(NoOrbDataException):
    """No data was found after applying the select criteria."""

    def __init(self, orbname, orb_select):
        """Initialize new OrbSelectException.

        Args:
            orbname (string): name of the orbserver
            orb_select (string): regex string

        """
        msg = 'No remaining sources in orb "%s" after orb.select with: "%s"' % (
            orbname,
            orb_select,
        )
        super(OrbSelectException, self).__init__(msg)
        self.orbname = orbname
        self.orb_select = orb_select


class OrbRejectException(NoOrbDataException):
    """No data was found after applying the reject criteria."""

    def __init__(self, orbname, orb_reject):
        """Initialize new OrbRejectException.

        Args:
            orbname (string): name of the orbserver
            orb_reject (string): regex string

        """
        msg = 'No remaining sources in orb "%s" after orb.reject with: "%s"' % (
            orbname,
            orb_reject,
        )
        super(OrbSelectException, self).__init__(msg)
        self.orbname = orbname
        self.orb_select = orb_reject


class PocError(PocException):
    """Base class for Poc errors."""

    def __init__(self, msg, original_exception):
        """Pass along the originalException."""
        super(PocError, self).__init__(msg + (": %s" % original_exception))
        self.original_exception = original_exception


class TooManyExtractError(PocError):
    """Too many consecutive data extractions failed."""

    def __init__(self):
        """Initialize TooManyExtractError."""
        msg = "More than " + str(MAX_EXTRACT_ERRORS) + " failures on orb.reap()"
        super(PocException, self).__init__(msg)


class ConfigurationError(PocError):
    """Configuration file is invalid."""

    pass


class OrbConnectError(PocException):
    """Couldn't connect to the orbserver."""

    def __init__(self, orbname, original_exception):
        """Generate custom error message for orb connections."""
        msg = "Cannot connect to orbserver at " + orbname
        super(OrbConnectError, self).__init(msg, original_exception)


class Poc:
    """Represent an individual Q330 POC packet."""

    def __init__(self):
        """Initialize the Poc object."""
        self._clean()

    def _clean(self):
        """Reset internal state."""
        self.id = False
        self.time = False
        self.strtime = False
        self.valid = False
        self.srcname = False
        self.sn = False
        self.srcip = False
        self.poctime = False
        self.pocc2 = {}
        self.rawpkt = {}

    def new(self, rawpkt):
        """Create a new Poc object, allowing reuse of an orb.Packet reference.

        This method is a hack around the memory leaks incurred by allocating a
        new orb.Packet structure repeatedly. Instead of allocating a new Pkt
        object and letting the garbage collector come around and free memory,
        we just repeatedly reuse the same object.
        """

        self._clean()

        self.rawpkt = rawpkt

        if not rawpkt[0] or int(float(rawpkt[0])) < 1:
            return

        self.id = rawpkt[0]
        self.time = rawpkt[2]

        # Try to extract information from packet
        pkt = Pkt.Packet(rawpkt[1], rawpkt[2], rawpkt[3])

        self.srcname = pkt.srcname if pkt.srcname else rawpkt[1]

        # Step around Antelope TypeError by explicitly calling
        # .keys() on the ParameterFile object.
        if "sn" in pkt.pf.keys():
            self.sn = pkt.pf["sn"]
        else:
            return

        if "srcip" in pkt.pf.keys():
            self.srcip = pkt.pf["srcip"]
        else:
            return

        if "time" in pkt.pf.keys():
            self.poctime = float(pkt.pf["time"])
            self.strtime = stock.epoch2str(self.poctime, "%D %H:%M:%S %Z").strip()
        else:
            return

        self.valid = True

        # Maybe we have some extra data...
        if "pocc2" in pkt.pf.keys():
            self.pocc2 = pkt.pf["pocc2"]
        else:
            self.pocc2 = {}

    def __str__(self):
        """Return string representation of Packet with internal details."""
        if self.valid:
            return "(%s) => [sn:%s ip:%s time:%s]" % (
                self.srcname,
                self.sn,
                self.srcip,
                self.poctime,
            )
        else:
            return "(**invalid**) => [pkid:%s pktsrc:%s pktime:%s]" % (
                self.rawpkt[0],
                self.rawpkt[1],
                self.rawpkt[2],
            )

    def data(self):
        """Return a dict representing the packet."""
        return {
            "pcktid": self.id,
            "time": int(self.poctime),
            "strtime": self.strtime,
            "srcname": "%s" % self.srcname,
            "srcip": self.srcip,
            "sn": self.sn,
            "pocc2": self.pocc2,
        }
