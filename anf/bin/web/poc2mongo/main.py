"""poc2mongo main module.

Implements the main function of the poc2mongo program.
"""

from optparse import OptionParser

from anf.getlogger import getAppLogger, getModuleLogger
from antelope import stock
from pymongo import MongoClient

from . import poc2mongo

logger = getModuleLogger(__name__)


def main(argv=None):
    """Run the soh2mongo program."""
    # Read configuration from command-line
    usage = "Usage: %prog [options]"

    parser = OptionParser(usage=usage)
    parser.add_option(
        "-s",
        action="store",
        dest="state",
        help="track orb id on this state file",
        default=False,
    )
    parser.add_option(
        "-c",
        action="store_true",
        dest="clean",
        help="clean 'drop' collection on start",
        default=False,
    )
    parser.add_option(
        "-v", action="store_true", dest="verbose", help="verbose output", default=False
    )
    parser.add_option(
        "-d", action="store_true", dest="debug", help="debug output", default=False
    )
    parser.add_option(
        "-p",
        "--pf",
        action="store",
        dest="pf",
        type="string",
        help="parameter file path",
        default="poc2mongo",
    )

    (options, args) = parser.parse_args()

    loglevel = "WARNING"
    if options.debug:
        loglevel = "DEBUG"
    elif options.verbose:
        loglevel = "INFO"

    # Need new object for logging work.
    logger = getAppLogger(__name__, loglevel=loglevel)

    # Get PF file values
    logger.info("Read parameters from pf file %s" % options.pf)
    pf = stock.pfread(options.pf)

    # Get MongoDb parameters from PF file
    mongo_user = pf.get("mongo_user")
    mongo_host = pf.get("mongo_host")
    mongo_password = pf.get("mongo_password")
    mongo_namespace = pf.get("mongo_namespace")
    mongo_collection = pf.get("mongo_collection")

    logger.debug("mongo_host => [%s]" % mongo_host)
    logger.debug("mongo_user => [%s]" % mongo_user)
    logger.debug("mongo_password => [%s]" % mongo_password)
    logger.debug("mongo_namespace => [%s]" % mongo_namespace)
    logger.debug("mongo_collection => [%s]" % mongo_collection)

    # Configure MongoDb instance
    try:
        logger.info("Init MongoClient(%s)" % mongo_host)
        mongo_instance = MongoClient(mongo_host)

        logger.info("Get namespace %s in mongo_db" % mongo_namespace)
        mongo_db = mongo_instance.get_database(mongo_namespace)

        logger.info("Authenticate mongo_db")
        mongo_db.authenticate(mongo_user, mongo_password)

    except Exception:
        logger.exception("Problem with MongoDB Configuration.")
        return -1

    # May need to nuke the collection before we start updating it
    # Get this mode by running with the -c flag.
    if options.clean:
        logger.info("Drop collection %s.%s" % (mongo_namespace, mongo_collection))
        mongo_db.drop_collection(mongo_collection)
        logger.info(
            "Drop collection %s.%s_errors" % (mongo_namespace, mongo_collection)
        )
        mongo_db.drop_collection("%s_errors" % mongo_collection)

    orbserver = pf.get("orbserver")
    logger.debug("orbserver => [%s]" % orbserver)

    orb_select = pf.get("orb_select")
    logger.debug("orb_select => [%s]" % orb_select)

    orb_reject = pf.get("orb_reject")
    logger.debug("orb_reject => [%s]" % orb_reject)

    default_orb_read = pf.get("default_orb_read")
    logger.debug("default_orb_read => [%s]" % default_orb_read)

    include_pocc2 = pf.get("include_pocc2")
    logger.debug("include_pocc2 => [%s]" % include_pocc2)

    reap_wait = pf.get("reap_wait")
    logger.debug("reap_wait => [%s]" % reap_wait)

    reap_timeout = pf.get("reap_timeout")
    logger.debug("reap_timeout => [%s]" % reap_timeout)

    timeout_exit = pf.get("timeout_exit")
    logger.debug("timeout_exit => [%s]" % timeout_exit)

    instance = poc2mongo(
        mongo_db[mongo_collection],
        orbserver,
        orb_select=orb_select,
        orb_reject=orb_reject,
        default_orb_read=default_orb_read,
        statefile=options.state,
        reap_wait=reap_wait,
        reap_timeout=reap_timeout,
        timeout_exit=timeout_exit,
    )

    logger.info("Starting poc2mongo instance.")
    return instance.get_pocs()