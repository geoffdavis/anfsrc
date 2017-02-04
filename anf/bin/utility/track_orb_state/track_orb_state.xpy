# We want a simple script that will track a few orbs
# and output the information in them in a condensed form.
#
# Juan Reyes
# reyes@ucsd.edu

import subprocess
import re


if len( sys.argv ) < 2:
    sys.exit( 'Need name of ORB(s).')

ORBS = sys.argv[1:]




# Loop over each orb listed on the configuration
for eachOrb in ORBS:

    cmd = subprocess.Popen('orbstat -vc %s' % eachOrb, shell=True, stdout=subprocess.PIPE)

    readline = 0
    inGroup = False
    inGroupStat = 15
    timeValue = False
    timeUnits = False

    for line in cmd.stdout:

        readline += 1

        if not line: continue

        line = line.rstrip()

        if re.search("fatal", line):
            print "\x1B[5m\x1B[41m\x1B[37m%s => %s\x1B[0m" %( eachOrb, line )
            break

        if inGroup:
            if re.search("Total", line): continue
            if re.search("nbytes", line): continue
            if re.search("errors", line): continue
            if re.search("selecting", line): continue
            if re.search("rejecting", line): continue
            if re.search("started", line): continue
            if re.search("^$", line): continue
            if re.search("-vc", line): continue

            if timeValue and timeUnits:

                if re.search("second", timeUnits):
                    print "\t[%s %s]    %s" % ( timeValue, timeUnits, line )
                elif re.search("minute", timeUnits):
                    print "\t[\x1B[91m%s %s]    %s\x1B[0m" %(  timeValue, timeUnits, line )
                elif re.search("hour", timeUnits):
                    print "\t[\x1B[41m%s %s]    %s\x1B[0m" %(  timeValue, timeUnits, line )
                else:
                    print "\t[\x1B[5m\x1B[41m\x1B[37m%s %s]    %s\x1B[0m" %(  timeValue, timeUnits, line )

                timeValue = False
                timeUnits = False

                continue

            elif len(line.split()) == inGroupStat:

                parts = line.split()

                timeValue = parts[-3]
                timeUnits = parts[-2]

                continue


            else:
                print 'UNKNOWN LINE [%s]' % line


        # Then we are reading the header....
        if readline < 4: continue
        if readline == 4:
            parts = line.split()
            print "\x1B[42m%s => %s\x1B[0m" % ( eachOrb, ' '.join( parts[3:] ) )
            continue

        if readline < 22: continue

        if readline == 22:
            inGroup = True
            continue
