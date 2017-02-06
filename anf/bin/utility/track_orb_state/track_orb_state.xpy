# We want a simple script that will track a few orbs
# and output the information in them in a condensed form.
#
# Juan Reyes
# reyes@ucsd.edu

import subprocess
import re
import json
from optparse import OptionParser


usage = '\nUSAGE:\n\t%s [-v] [-j] orb1 [orb2] [orb3] ... \n\n' % __file__

parser = OptionParser()

parser.add_option("-v",  dest="verbose", help="Verbose output",
                    action="store_true",default=False)
parser.add_option("-j",  dest="json", help="JSON data output",
                    action="store_true",default=False)

(options, ORBS) = parser.parse_args()

if len(ORBS) < 1:
    parser.print_help()
    sys.exit( 'Need name of ORB(s).')



def output_line( text ):
    if options.json: return
    else: print text


json_cache = {}

# Loop over each orb listed on the configuration
for eachOrb in ORBS:

    cmd = subprocess.Popen('orbstat -vc %s' % eachOrb, shell=True, stdout=subprocess.PIPE)

    readline = 0
    inGroup = False
    inGroupStat = 15
    timeValue = False
    timeUnits = False

    json_cache[ eachOrb ] = { 'status': 'unknown', 'orbs': [] }

    for line in cmd.stdout:

        readline += 1

        if not line: continue

        line = line.rstrip()

        if re.search("fatal", line):
            output_line( "\x1B[5m\x1B[41m\x1B[37m%s => %s\x1B[0m" %( eachOrb, line ) )
            json_cache[ eachOrb ][ 'status' ] = line
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
                    output_line( "\t[%s %s]    %s" % ( timeValue, timeUnits, line ) )
                    state = 'ok'
                elif re.search("minute", timeUnits):
                    output_line( "\t[\x1B[91m%s %s]    %s\x1B[0m" %(  timeValue, timeUnits, line ) )
                    state = 'watch'
                elif re.search("hour", timeUnits):
                    output_line( "\t[\x1B[41m%s %s]    %s\x1B[0m" %(  timeValue, timeUnits, line ) )
                    state = 'warning'
                else:
                    output_line( "\t[\x1B[5m\x1B[41m\x1B[37m%s %s]    %s\x1B[0m" %(  timeValue, timeUnits, line ) )
                    state = 'error'

                json_cache[ eachOrb ][ 'orbs' ].append(
                        {
                            'state': state,
                            'orbname': line,
                            'time': timeValue,
                            'timeUnits': timeUnits
                        }
                        )

                timeValue = False
                timeUnits = False

                continue

            elif len(line.split()) == inGroupStat:

                parts = line.split()

                timeValue = parts[-3]
                timeUnits = parts[-2]

                continue


            else:
                output_line( 'UNKNOWN LINE [%s]' % line )


        # Then we are reading the header....
        if readline < 4: continue
        if readline == 4:
            parts = line.split()
            output_line( "\x1B[42m%s => %s\x1B[0m" % ( eachOrb, ' '.join( parts[3:] ) ) )
            json_cache[ eachOrb ][ 'status' ] = ' '.join( parts[3:] )
            continue

        if readline < 22: continue

        if readline == 22:
            inGroup = True
            continue


if options.json:
    print "\n%s\n" % json.dumps(json_cache, indent=4, separators=(',', ': '))
