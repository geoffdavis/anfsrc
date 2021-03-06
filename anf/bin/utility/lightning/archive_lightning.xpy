"""
    The Earth Networks lightning sensor network,
    known as the Earth Networks Total Lightning
    Network (ENTLN), is the worlds largest
    lightning detection network.

    Part of the collaboration process is to migrate some
    lightning data into Antelope's databases. This script
    translate from their native CSV into a CSS3.0 database.


    From EarthNetworks:
        Christopher D. Sloop <CSloop@earthnetworks.com>
        Amena Ali <aali@earthnetworks.com>

    From ANF:
        Juan Reyes <reyes@ucsd.edu>

    06/2012

"""

"""
    Format of csv files:

    [
        'LtgFlashPortions_History_ID',
        'FlashPortionGUID',
        'FlashGUID',
        'Lightning_Time',
        'Lightning_Time_String',
        'Latitude',
        'Longitude',
        'Height',
        'Stroke_Type',
        'Amplitude',
        'Stroke_Solution',
        'Offsets',
        'Confidence',
        'LastModifiedTime',
        'LastModifiedBy'
    ]

    Example:
    [
        '739400180',
        '0bed8ee4-a98a-4d21-a00d-7e8974ff12dc',
        '80b52373-41b3-43c8-9c57-4ddc11a81e34',
        '4/27/2011 1:02:26 AM',
        '2011-04-27T01:02:26.294541299',
        '39.9451159',
        '-78.7135798',
        '9952.9',
        '1',
        '3967',
        'Sensor: offset@err(num;dev;+peak;-peak)=
            HANMH:0@0.206(17;0;18619;)
            VNDRG:175@0.212(13;0;1632;)
            PHILP:305@-0.143(5;0;1135;)
            MNCMG:360@-0.281(9;0;897;)
            RSTFM:361@0.488(9;0;2035;)
            MRCRM:465@0.116(5;0;1326;)
            SE4DC:469@0.047(11;0;996;) ',
        'HANMH=0',
        'VNDRG=175',
        'PHILP=305',
        'MNCMG=360',
        'RSTFM=361',
        'MRCRM=465',
        'SE4DC=469',
        '',
        '100',
        '4/26/2011 9:04:55 PM',
        'LtgInsertFlashPortion_pr'
    ]


    The mapping from the csv to the css3.0 is:
        'lat', Latitude,
        'lon', Longitude,
        'depth', Height,
        'orid', subset of their FlashPortionGUID,
        'evid', subset of their FlashGUID,
        'time', Lightning_Time_String,
        'commid', Amplitude,
        'review', Confidence,
        'etype',Stroke_Type,
        'lddate', LastModifiedTime,
        'auth', LastModifiedBy

"""

import os, sys
import csv
from collections import defaultdict

import antelope.datascope as datascope
import antelope.stock as stock

def main():
    """ Get each event and output the time
    in UTC, Local and Pacific.
    """
    # {{{ main

    if len(sys.argv) != 3:
        sys.exit('USAGE: archive_lightning datafile database [got:%s]\n\n' % sys.argv)

    # Get options from command-line
    if sys.argv[1]:
        source = os.path.abspath(sys.argv[1])
    else:
        sys.exit( 'Need to provide source file for data' )

    if sys.argv[2]:
        database = os.path.abspath(sys.argv[2])
    else:
        sys.exit( 'Need to provide destination database name' )

    # Verify that file exists
    if not os.path.isfile(source):
        sys.exit("File '%s' does not exist, verify file." % source)

    # Verify database
    try:
        db = datascope.dbopen(database,"r+")
    except Exception as e:
        sys.exit( 'Problems opening database "%s": %s' % (database,e) )

    if not db.query(datascope.dbDATABASE_IS_WRITABLE):
        sys.exit( 'Problems opening database "%s": \n %s' % (database,db) )

    try:
        db = datascope.dblookup (db, table = 'origin')
    except Exception as e:
        sys.exit( 'Problems opening origin table. %s \n %s' % (e,db) )

    if not db.query(datascope.dbTABLE_IS_WRITEABLE):
        sys.exit( 'Problems opening table origin. \n %s' % db)


    # track orids
    orid_list = defaultdict()
    event_list = defaultdict()
    last_orid = 0
    last_evid = 0
    orid = 0
    evid = 0
    with open(source, 'rb') as f:
        reader = csv.reader(f)
        try:
            for row in reader:

                print("\nNew line:\n")
                print("\t%s\n" % row)
                #print "line: %s" % reader.line_num
                if reader.line_num == 1: continue
                # for testing lets stop at 50
                #if reader.line_num == 50: break

                # Parse elements of each row.
                try:
                    long_orid   = row[1]
                    long_evid   = row[2]

                    # #############################################
                    # # Lets build generic id's for now.
                    # orid   = row[1]
                    # evid   = row[2]
                    # # Convert ids to 8 character ints.
                    # old = orid
                    # orid = hashlib.sha256(orid)
                    # orid = str(int(orid.hexdigest(), base=16))
                    # print "\tConvert orid %s => %s" % (old,orid)
                    # orid = int(orid[-8:])
                    # print "\tGet only last 8 digits: %s" % orid

                    # # Convert ids to 8 character ints.
                    # old = evid
                    # evid = hashlib.sha256(evid)
                    # evid = str(int(evid.hexdigest(), base=16))
                    # print "\tConvert evid %s => %s" % (old,evid)
                    # evid = int(evid[-8:])
                    # print "\tGet only last 8 digits: %s" % evid
                    # #############################################



                    # we need unique evid
                    print("\t\tget evid for : %s" % long_evid)
                    if long_evid in event_list:
                        evid = event_list[long_evid]
                    else:
                        # increase counter
                        last_evid = last_evid + 1
                        evid = last_evid
                        # keep track of orids
                        event_list[long_evid] = evid
                        if evid > 99999999:
                            sys.exit("Too many evids: %s" % evid )
                    print("\t\tevid: %s" % evid)

                    # we need unique orid
                    print("\t\tget orid for : %s" % long_orid)
                    if long_orid in orid_list:
                        orid = orid_list[long_orid]
                    else:
                        # increase counter
                        last_orid = last_orid + 1
                        orid = last_orid
                        # keep track of orids
                        orid_list[long_orid] = orid
                        if orid > 99999999:
                            sys.exit("Too many orid: %s" % orid )
                    print("\t\torid: %s" % orid)

                    #
                    # OLD METHOD
                    #
                    # We don't translate from the original but now we
                    # create new ids.
                    #
                    # we need unique orids
                    # print "\t\tTry orid: %s" % orid
                    # while long_orid in orid_list:
                    #     print "\t\torid: %s in list!!!" % orid
                    #     if orid_list[orid] == row[1]:
                    #         orid = orid + 1
                    #         print "\t\torid + 1: %s" % orid
                    #         if orid > 99999999:
                    #             sys.exit("Too many orids: %s" % orid )
                    #         print "\t\tTry new orid: %s" % orid
                    # # keep track of orids
                    # orid_list[orid] = row[1]

                    # Convert time of event
                    date   = str(row[4]).replace('T', ' ')
                    time   = stock.str2epoch(date)
                    print("\tConvert %s => %s" % (row[4],time))

                    # Position
                    lat    = float(row[5])
                    lon    = float(row[6])
                    elev   = float(row[7]) / 1000 #change to km
                    print("\tLocation (%s, %s, %s)" % (lat, lon, elev))

                    # Params
                    type   =  'IC' if row[8] == '1' else 'CG'
                    print("\tType: %s" % type)

                    amps   = int(row[9])
                    print("\tAmplitude: %s" % amps)

                    # from the back of the array to the front
                    conf   = row[-3]
                    print("\tConfidence: %s" % conf)

                    lddate = row[-2]
                    lddate = stock.str2epoch(lddate)
                    print("\tLastModified: %s => %s" % (row[-2],lddate))

                    auth   = '%s' % row[-1].split()[0][0:14]
                    print("\tAuth: %s" % auth)


                except Exception as e:
                    sys.exit('Problem converting values from file %s, line %d: %s \n %s' % (source,reader.line_num,row,e))

                if abs(float(lat)) > 90:
                    sys.exit("\t\tERROR in value for lat: [%s]" % lat)
                if abs(float(lon)) > 180:
                    sys.exit("\t\tERROR in value for lon: [%s]" % lon)
                if time > stock.now() or time < 0:
                    sys.exit("\t\tERROR in value for time: [%s]" % time)

                print("Adding record (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s" \
                    % (lat, lon, elev, orid, evid, time, amps, conf, type, lddate, auth))

                try:
                    db.addv(
                            'nass',999,
                            'ndef',999,
                            'lat', lat,
                            'lon', lon,
                            'depth', elev,
                            'orid', orid,
                            'evid', evid,
                            'time', time,
                            'commid', amps,
                            'review', conf,
                            'etype',type,
                            'lddate', lddate,
                            'auth', auth)

                except Exception as e:
                    sys.exit('Problem updating database: %s %s' % (Exception,e))


        except csv.Error as e:
            sys.exit('Problem with file %s, line %d: %s' % (source, reader.line_num, e))



    db.close()

    return 0
    # }}}

if __name__ == '__main__':
    status = main()
    sys.exit(status)
else:
    raise Exception("Not a module to be imported!")
    sys.exit()
