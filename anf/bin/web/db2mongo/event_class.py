"""The db2mongo event module."""
from datetime import datetime
import json
from logging import getLogger

from anf.logutil import fullname
import antelope.datascope as datascope
import antelope.stock as stock

from .util import (
    db2mongoException,
    extract_from_db,
    get_md5,
    parse_sta_time,
    readable_time,
    test_table,
    verify_db,
)

logger = getLogger(__name__)


class eventException(db2mongoException):
    """Base class for exceptions raised by this module."""


class Events:
    """db2mongo module to query a Datascope event database and cache.

    The origin table is the main source of information. The system will try to join with the event table if present. The netmag table will be imported into memory and used to expand the events.

    Usage:
        events = Events(db,subset=False)

        events.validate()

        while True:
            if events.need_update():
                events.update()
                data,error = events.data()
            sleep(time)

    """

    def __init__(self, db=False, subset=False):
        """Initilized the db2mongo event module."""
        self.logger = getLogger(fullname(self))

        self.logger.debug("Events.init()")

        self.db = False
        self.database = False
        self.db_subset = False
        self.cache = []
        self.cache_error = []
        self.mags = {}

        # event table is not tested here.
        self.tables = ["origin", "netmag"]
        self.dbs_tables = {}

        self.timeformat = False
        self.timezone = False

    def validate(self):
        """Validate the module configuration."""
        self.logger.debug("validate()")

        if self.db:
            return True

        # Vefiry database files
        if self.database:
            if verify_db(self.database):
                self.db = self.database
            else:
                raise eventException("Not a vaild database: %s" % (self.database))
        else:
            raise eventException("Missing value for database")

        # Verify tables
        for table in self.tables:
            path = test_table(self.db, table)
            if not path:
                raise eventException("Empty or missing: %s %s" % (self.db, table))

            self.dbs_tables[table] = {"path": path, "md5": False}
            self.logger.debug("run validate(%s) => %s" % (table, path))

        return True

    def need_update(self):
        """Check if the md5 checksum changed on any table."""
        self.logger.debug("need_update()")

        for name in self.tables:

            md5 = self.dbs_tables[name]["md5"]
            test = get_md5(self.dbs_tables[name]["path"])

            self.logger.debug(
                "(%s) table:%s md5:[old: %s new: %s]" % (self.db, name, md5, test)
            )

            if test != md5:
                return True

        return False

    def update(self):
        """Update the data from the tables."""

        if not self.db:
            self.validate()

        self.logger.debug("update(%s)" % (self.db))

        for name in self.tables:
            self.dbs_tables[name]["md5"] = get_md5(self.dbs_tables[name]["path"])

        self._get_magnitudes()
        self._get_events()

    def data(self, refresh=False):
        """Export the data from the tables.

        Args:
            refresh (boolean): force an update to the cache. False by default.
        """
        self.logger.debug("data(%s)" % (self.db))

        if not self.db:
            self.validate()

        if refresh:
            self.update()

        return (self._clean_cache(self.cache), self._clean_cache(self.cache_error))

    def _get_magnitudes(self):
        """Get all mags from the database into memory."""

        self.logger.debug("Get magnitudes ")

        self.mags = {}

        steps = ["dbopen netmag", "dbsubset orid != NULL"]

        fields = [
            "orid",
            "magid",
            "magnitude",
            "magtype",
            "auth",
            "uncertainty",
            "lddate",
        ]

        for v in extract_from_db(self.db, steps, fields):
            orid = v.pop("orid")
            self.logger.debug("new mag for orid:%s" % orid)

            try:
                v["strmag"] = "%0.1f %s" % (float(v["magnitude"]), v["magtype"])
            except Exception:
                v["strmag"] = "-"

            if orid not in self.mags:
                self.mags[orid] = {}

            self.mags[orid][v["magid"]] = v

    def _get_events(self):
        """Update all orids/evids from the database."""
        self.cache = []

        # Test if we have event table
        with datascope.closing(datascope.dbopen(self.db, "r")) as db:
            dbtable = db.lookup(table="event")
            if dbtable.query(datascope.dbTABLE_PRESENT):
                steps = ["dbopen event"]
                steps.extend(["dbjoin origin"])
                steps.extend(["dbsubset origin.orid != NULL"])
                steps.extend(["dbsubset origin.orid == prefor"])
                fields = ["evid"]
            else:
                steps = ["dbopen origin"]
                steps.extend(["dbsubset orid != NULL"])
                fields = []

        fields.extend(
            ["orid", "time", "lat", "lon", "depth", "auth", "nass", "ndef", "review"]
        )

        for v in extract_from_db(self.db, steps, fields, self.db_subset):
            if "evid" not in v:
                v["evid"] = v["orid"]

            self.logger.debug("Events(): new event #%s" % v["evid"])

            v["allmags"] = []
            v["magnitude"] = "-"
            v["maglddate"] = 0
            v["srname"] = "-"
            v["grname"] = "-"
            v["time"] = parse_sta_time(v["time"])
            v["strtime"] = readable_time(v["time"], self.timeformat, self.timezone)

            try:
                v["srname"] = stock.srname(v["lat"], v["lon"])
            except Exception as e:
                self.logger.warning(
                    "Problems with srname for orid %s: %s"
                    % (v["orid"], v["lat"], v["lon"], e)
                )

            try:
                v["grname"] = stock.grname(v["lat"], v["lon"])
            except Exception as e:
                self.logger.warning(
                    "Problems with grname for orid %s: %s"
                    % (v["orid"], v["lat"], v["lon"], e)
                )

            orid = v["orid"]
            if orid in self.mags:
                for o in self.mags[orid]:
                    v["allmags"].append(self.mags[orid][o])
                    if self.mags[orid][o]["lddate"] > v["maglddate"]:
                        v["magnitude"] = self.mags[orid][o]["strmag"]
                        v["maglddate"] = self.mags[orid][o]["lddate"]

            self.cache.append(v)

    def _clean_cache(self, cache):

        results = []

        for entry in cache:
            # Convert to JSON then back to dict to stringify numeric keys
            entry = json.loads(json.dumps(entry))

            # Generic id for this entry
            entry["id"] = entry["evid"]

            # add entry for autoflush index
            entry["time_obj"] = datetime.fromtimestamp(entry["time"])

            # add entry for last load of entry
            entry["lddate"] = datetime.fromtimestamp(stock.now())

            results.append(entry)

        return results
