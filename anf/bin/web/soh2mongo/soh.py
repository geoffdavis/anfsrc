"""The soh2mongo soh module."""
from datetime import datetime
import logging
import re
import warnings

from anf.logutil import fullname
from antelope import orb, stock

from .dlmon import Dlmon
from .packet import Packet
from .statefile import stateFile
from .util import TooManyOrbExtractErrors

MAX_EXTRACT_ERRORS = 10

logger = logging.getLogger(__name__)


class SOH_mongo:
    """Read an ORB for pf/st and pf/im packets and update a MongoDatabase.

    We can run with the clean option and clean the archive before we start
    putting data in it.  There is a position flag to force the reader to
    jump to a particular part of the ORB and the usual statefile to look
    for a previous value for the last packet id read.

    """

    def __init__(
        self,
        collection,
        orbname,
        orb_select=None,
        orb_reject=None,
        default_orb_read=0,
        statefile=None,
        reap_wait=3,
        timeout_exit=True,
        reap_timeout=5,
        parse_opt=False,
        indexing=[],
    ):
        """Intialize the SOH_mongo object.

        Params:
            There's a lot of them. Good luck.

            collection (mongodb thingy): a collection handle from an active
            mongodb connection.
            orbname (string): orbserver name (hostname:port or :port)
            orb_select (string): pattern for source names to selection, or None
            orb_reject (string): pattern for source names to reject, or None
            default_orb_read (string or int): starting packet position.
            Defaults to 0.
            stateFile (string or None): path to statefile. If none specified (default), no state is tracked
            reap_wait (int): how long in seconds to wait between orb reaps calls. Default is 3 seconds.
            timeout_exit (bool): Exit if a request times out? Defaults to True.
            reap_timeout (int): how long to wait for a request before it times out. Defaults to 5 seconds.
            parse_opt (bool): Parse the extra OPT channels from a Q330? Defaults to False.
            indexing (dict): list of keys to index on. Default is empty list.
        """
        self.logger = logging.getLogger(fullname(self))
        self.logger.debug("Initializing SOHMongo object.")

        self.dlmon = Dlmon(parse_opt)
        self.packet = Packet()
        self.cache = {}
        self.orb = None
        self.errors = 0
        self.orbname = orbname
        self.lastread = 0
        self.timezone = "UTC"
        self.position = False
        self.error_cache = {}
        self.indexing = indexing
        self.statefile = statefile
        self.collection = collection
        self.orb_select = orb_select
        self.orb_reject = orb_reject
        self.reap_wait = int(reap_wait)
        self.timeout_exit = timeout_exit
        self.reap_timeout = int(reap_timeout)
        self.timeformat = "%D (%j) %H:%M:%S %z"
        self.default_orb_read = default_orb_read

        # StateFile
        self.state = stateFile(self.statefile, self.default_orb_read)
        self.position = self.state.last_packet()
        # self.last_time = self.state.last_time()

        self.logger.debug("Need ORB position: %s" % self.position)

        if not self.orb_select:
            self.orb_select = None
        if not self.orb_reject:
            self.orb_reject = None

    def start_daemon(self):
        """Run in a daemon mode."""

        self.logger.debug("Update ORB cache")

        self.logger.debug(self.orbname)

        if not self.orbname or not isinstance(self.orbname, str):
            raise LookupError("Problems with orbname [%s]" % (self.orbname))

        # Expand the object if needed
        if not self.orb:
            self.logger.debug("orb.Orb(%s)" % (self.orbname))
            self.orb = {}
            self.orb["orb"] = None
            self.orb["status"] = "offline"
            self.orb["last_success"] = 0
            self.orb["last_check"] = 0

        self._connect_to_orb()

        while True:
            # Reset the connection if no packets in reap_timeout window
            self.logger.debug("starting next reap cycle")
            if (
                self.orb["last_success"]
                and self.reap_timeout
                and ((stock.now() - self.orb["last_success"]) > self.reap_timeout)
            ):
                self.logger.warning("Possible stale ORB connection %s" % self.orbname)
                if stock.yesno(self.timeout_exit):
                    break
                else:
                    self._connect_to_orb()

            self.logger.debug("calling extract_data")
            if self._extract_data():
                self.logger.debug("Success on extract_data(%s)" % (self.orbname))
            else:
                self.logger.warning("Problem on extract_data(%s)" % (self.orbname))

        self.orb["orb"].close()

        return 0

    def _test_orb(self):
        """Verify the orb is responsive."""
        self.orb["status"] = self.orb["orb"].ping()

        self.logger.debug("orb.ping() => %s" % (self.orb["status"]))

        if int(self.orb["status"]) > 0:
            return True

        return False

    def _connect_to_orb(self):
        """Connect or reconnect to a given orbserver."""
        self.logger.debug("start connection to orb: %s" % (self.orbname))
        if self.orb["status"]:
            try:
                self.logger.debug("close orb connection %s" % (self.orbname))
                self.orb["orb"].close()
            except Exception:
                pass

        try:
            self.logger.debug("connect to orb(%s)" % self.orbname)
            self.orb["orb"] = orb.Orb(self.orbname)
            self.orb["orb"].connect()
            self.orb["orb"].stashselect(orb.NO_STASH)
        except Exception as e:
            raise Exception("Cannot connect to ORB: %s %s" % (self.orbname, e))

        # self.logger.info( self.orb['orb'].stat() )

        if self.orb_select:
            self.logger.debug("orb.select(%s)" % self.orb_select)
            if not self.orb["orb"].select(self.orb_select):
                raise Exception("NOTHING LEFT AFTER orb.select(%s)" % self.orb_select)

        if self.orb_reject:
            self.logger.debug("orb.reject(%s)" % self.orb_reject)
            if not self.orb["orb"].reject(self.orb_reject):
                raise Exception("NOTHING LEFT AFTER orb.reject(%s)" % self.orb_reject)

        self.logger.debug("ping orb: %s" % (self.orb["orb"]))

        try:
            if int(self.position) > 0:
                self.logger.info("Go to orb position: %s" % (self.position))
                self.orb["orb"].position("p%d" % int(self.position))
            else:
                raise
        except Exception:
            try:
                self.logger.info(
                    "Go to orb default position: %s" % (self.default_orb_read)
                )
                self.orb["orb"].position(self.default_orb_read)
            except Exception as e:
                self.logger.error("orb.position: %s, %s" % (Exception, e))

        try:
            self.logger.info("orb.tell()")
            self.logger.info(self.orb["orb"].tell())
        except orb.OrbTellError:
            self.logger.info("orb.seek( orb.ORBOLDEST )")
            # self.logger.info( self.orb['orb'].seek( orb.ORBOLDEST ) )
            self.logger.info(self.orb["orb"].after(0))
        except Exception as e:
            self.logger.error("orb.tell() => %s, %s" % (Exception, e))

        # try:
        #    self.logger.debug( "orb position: %s" % (self.orb['orb'].tell()) )
        # except Exception,e:
        #    self.orb['orb'].after(0)
        #    self.orb['orb'].position(self.default_orb_read)
        #    try:
        #        self.logger.debug( "orb position: %s" % (self.orb['orb'].tell()) )
        #    except Exception,e:
        #        self.logger.error( "orb position: %s,%s" % (Exception,e) )

        if not self._test_orb():
            raise Exception("Problems connecting to (%s)" % self.orbname)

    def _extract_data(self):
        """Reap data from orb packets."""

        self.orb["last_check"] = stock.now()

        if self.errors > MAX_EXTRACT_ERRORS:
            raise TooManyOrbExtractErrors(
                "%s consecutive errors on orb.reap()" % MAX_EXTRACT_ERRORS
            )

        try:
            # REAP new packet from ORB
            # Squelch RuntimeWarnings from the Antelope layer
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                pktbuf = self.orb["orb"].reap(self.reap_wait)
                # Extract packet into our internal object
                self.packet.new(pktbuf)

        except orb.OrbIncompleteException as e:
            self.logger.debug("Caught OrbIncompleteException: " + str(e), exc_info=True)
            self.errors = 0
            return True

        except stock.PfException:
            self.logger.exception("Couldn't read from pf packet.")
            self.error += 1
            return False

        except Exception:
            self.logger.exception(
                "Unknown Exception occurred while extracting data(%s)" % (self.orbname)
            )
            self.errors += 1
            return False

        self.logger.debug("_extract_data(%s,%s)" % (self.packet.id, self.packet.time))

        # reset error counter
        self.errors = 0

        if not self.packet.id or not self.packet.valid:
            self.logger.debug("_extract_data() => Not a valid packet")
            return False

        # save ORB id to state file
        self.state.set(self.packet.id, self.packet.time)

        self.logger.debug("errors:%s" % self.errors)

        if self.packet.valid:
            self.logger.debug("%s" % self.packet)
            # we print this on the statusFile class too...
            self.logger.debug(
                "orblatency %s" % (stock.strtdelta(stock.now() - self.packet.time))
            )
            self.position = self.packet.id
            self.logger.debug("orbposition %s" % self.position)
            self.orb["last_success"] = stock.now()

            self._update_collection()
        else:
            self.logger.debug(
                "invalid packet: %s %s" % (self.packet.id, self.packet.srcname)
            )
            return False

        return True

    def _update_collection(self):
        """Update the mongodb collection."""

        self.logger.debug("update_collection()")

        # Verify if we need to update MongoDB
        if self.packet.valid:
            self.logger.debug("collection.update()")

            # Loop over packet and look for OPT channels
            for snetsta in self.packet:

                self.logger.info("Update entry: %s" % snetsta)
                documentid = "%s-%s" % (
                    snetsta,
                    str(self.packet.srcname).replace("/", "-"),
                )

                parts = snetsta.split("_")

                # self.logger.debug( self.packet.dls[snetsta] )

                # Use dlmon class to parse all values on packet
                self.dlmon.new(self.packet.dls[snetsta])

                # expand object with some info from packet
                self.dlmon.set("station", snetsta)
                self.dlmon.set("srcname", str(self.packet.srcname).replace("/", "-"))
                self.dlmon.set("pckttime", self.packet.time)
                self.dlmon.set("pcktid", self.packet.id)
                try:
                    self.dlmon.set("snet", parts[0])
                except Exception:
                    self.dlmon.set("snet", "unknown")
                try:
                    self.dlmon.set("sta", parts[1])
                except Exception:
                    self.dlmon.set("sta", "unknown")

                if self.packet.imei:
                    self.dlmon.set("imei", self.packet.imei)
                if self.packet.q330:
                    self.dlmon.set("q330", self.packet.q330)

                # add entry for autoflush index
                self.dlmon.set("time_obj", datetime.fromtimestamp(self.packet.time))

                # self.logger.error( self.packet.dls[snetsta] )
                # self.logger.debug( self.dlmon.dump() )

                # self.collection.update({'id': snetsta}, {'$set':self.packet.dls[snetsta]}, upsert=True)
                self.collection.update(
                    {"id": documentid}, {"$set": self.dlmon.dump()}, upsert=True
                )
                # self.logger.error( 'end test' )

            # Create/update some indexes for the collection
            self._index_db()

    def _index_db(self):
        """Set index values on MongoDB collection."""

        self.logger.debug("index_db()")

        # Stop if we don't have any index defined.
        if not self.indexing or len(self.indexing) < 1:
            return

        re_simple = re.compile(".*simple.*")
        re_text = re.compile(".*text.*")
        re_sparse = re.compile(".*sparse.*")
        re_hashed = re.compile(".*hashed.*")
        re_unique = re.compile(".*unique.*")

        for field, param in self.indexing.iteritems():

            unique = 1 if re_unique.match(param) else 0
            sparse = 1 if re_sparse.match(param) else 0

            style = 1
            if re_text.match(param):
                style = "text"
            elif re_hashed.match(param):
                style = "hashed"
            elif re_simple.match(param):
                style = 1

            try:
                expireAfter = float(param)
            except Exception:
                expireAfter = False

            self.logger.debug(
                "ensure_index( [(%s,%s)], expireAfterSeconds = %s, unique=%s, sparse=%s)"
                % (field, style, expireAfter, unique, sparse)
            )
            self.collection.ensure_index(
                [(field, style)],
                expireAfterSeconds=expireAfter,
                unique=unique,
                sparse=sparse,
            )

        self.collection.reindex()
