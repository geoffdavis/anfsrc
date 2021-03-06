##############################################################################
# Name          : Plot traces
# Purpose       : Simple scirpt to plot segments
# ARGUMENTS     : database [start] [end]
# FLAGAS        : [-d] [-v] [-a] [-j skip_traces] [-p pf] [-n ./output_file]
#               : [-f filter] [-e event_id] [-s wfdisc_subset_regex]
# Author        : Juan Reyes
#
#
#EXAMPLE:   plot_traces -a -v /opt/antelope/data/db/demo/demo 706139724 706139815
#EXAMPLE:   plot_traces -a -v -e 645 /opt/antelope/data/db/demo/demo
##############################################################################

import antelope.datascope as datascope
import antelope.stock as stock

import os
import sys
import json
import re
from optparse import OptionParser
import matplotlib.transforms as transforms
import numpy as np
import matplotlib.pyplot as plt
from anf.str2bool import str2bool

import logging
logging.basicConfig(
    format='plot_traces[%(levelname)s]: %(message)s',
    level=logging.WARNING
)
logging.addLevelName(45, "NOTIFY")
logger = logging.getLogger()

def notify(msg=''):
    if not isinstance(msg, str):msg = pprint(msg)
    logger.log(45,msg)

def log(msg=''):
    if not isinstance(msg, str):msg = pprint(msg)
    logger.info(msg)

def warning(msg=''):
    if not isinstance(msg, str):msg = pprint(msg)
    logger.warning(msg)

def error(msg=''):
    if not isinstance(msg, str):msg = pprint(msg)
    logger.error(msg)
    sys.exit(msg)

def pprint(msg):
    return "\n%s\n" % json.dumps(msg, indent=4, separators=(',', ': '))


#import pylab

def get_pf_params(pf_file):
    # Look for values in pf file
    pf = stock.pfupdate(pf_file)

    # default to black
    tableau20 = pf.get('tableau20', defaultval=[(0,0,0)])

    # Need to convert from strings
    tableau20 = [eval(x) for x in tableau20]

    # Scale the RGB values to the [0, 1] range, which is the format matplotlib accepts.
    for i in range(len(tableau20)):
        r, g, b = tableau20[i]
        tableau20[i] = (r / 255., g / 255., b / 255.)

    # default to white
    line_w = float(pf.get('line_width', defaultval=1.5))

    # default to white
    add_shadow = str2bool( pf.get('add_shadow', defaultval='True') )

    # default to white
    background = pf.get('background', defaultval=[(255,255,0)])

    # format of time ticks
    timeformat = pf.get('time_format', defaultval='%D\n%H:%M:%S UTC')

    # default to white
    figsize = pf.get('image_size', defaultval=(20,15) )
    figsize = eval(figsize)

    # time window if we have event mode
    timewindow = pf.get('timewindow', defaultval=(60,300) )
    timewindow = eval(timewindow)

    return (tableau20,background,figsize,timeformat,line_w,timewindow,add_shadow)



def extract_data(db,start,end,sites,subset=False):
    '''
    Get a database object and extract the important
    data from it.
    '''

    attempt = -1
    total = 0
    stations = {}

    steps = ['dbopen wfdisc']
    steps.extend(['dbjoin snetsta'])
    if subset: steps.extend(['dbsubset %s' % subset])
    steps.extend(['dbsubset endtime> %s' % start])
    steps.extend(['dbsubset time < %s' % end])

    log( steps )

    with datascope.freeing(db.process( steps )) as dbwfdisc:
        # The dict of site is in reversed order
        for sta in reversed([x[0] for x in sites]):
            parts = sta.split('_')
            with datascope.freeing(dbwfdisc.subset('snet =~/%s/ && sta =~ /%s/' % (parts[0],parts[1]))) as dbview:
                dbview = dbview.sort(['sta','chan'])

                if options.jump >  dbview.record_count or not options.jump:
                    jump = 1
                else:
                    jump = options.jump

                for temp in dbview.iter_record():
                    (n,s,c) = temp.getv('snet','sta','chan')
                    log('\tverify %s_%s_%s' % (n,s,c) )

                    snetsta = "%s_%s" % (n, s)

                    if snetsta in stations and c in stations[snetsta]:
                        log('\t[%s_%s] Already processed\n' % ( snetsta, c ) )
                        continue
                    else:
                        log('\tValid %s_%s_%s' % (n,s,c) )

                    # Hard limit on stations/traces
                    if total >= int(options.maxtraces):
                        log('\tGot [%s] Max number of traces [%s]\n' % ( total, options.maxtraces ) )
                        continue
                    else:
                        log('\tOnly %s for now' % total )

                    attempt += 1
                    if attempt%int(jump):
                        log('\tJump trace: attempt[%s]\n' % attempt )
                        continue
                    else:
                        log('\tAttempt:%s Jump:%s' % (attempt, jump) )

                    try:
                        log('\textract %s_%s_%s' % (n,s,c) )
                        log('\ttrsample(%s,%s,%s,%s)' % (start, end, s, c) )
                        data = dbview.trsample(start, end, s, c, apply_calib=True, filter=options.filter )
                    except Exception as e:
                        warning('\nProblem during trloadchan %s %s %s %s [%s]\n' % (start,end,s,c,e))
                        continue

                    log('\tGot data. Normalize and store' )
                    try:
                        if len(data):
                            # Flatten that list of touples
                            data = [item for sublist in data for item in sublist]
                            t =  np.array(data[0::2])
                            d =  np.array(data[1::2])
                            if not len(t): continue
                            if not len(d): continue

                            min_v = min(d)
                            max_v = max(d)
                            if not min_v: continue
                            if not max_v: continue

                            # Normalize 0-1
                            d -=  min_v
                            d /=  (max_v-min_v)

                            if not sta in stations: stations[sta] = {}
                            stations[sta][c] = (t,d)
                    except Exception as e:
                        notify('\nProblem on data parsing %s: %s \n' % (Exception,e))

                    log('\tDone with %s_%s' % (sta,c) )

                    total += 1

    return (stations,total)


def get_arrivals(db,start=False,end=False,event=False,subset=False):
    '''
    Extract all valid arrivals from db.
    '''

    arrivals = {}
    min_a = 9999999999999999
    max_a = 0

    event_table = db.lookup(table='event')
    log('event table present: %s' % event_table.query(datascope.dbTABLE_PRESENT) )
    if event:
        if event_table.query(datascope.dbTABLE_PRESENT):
            steps = ['dbopen event']
            steps.extend(['dbjoin origin'])
            steps.extend(['dbsubset evid==%s && prefor==orid' % event])
        else:
            steps = ['dbopen origin']
            steps.extend(['dbsubset orid==%s' % event ])

        steps.extend(['dbjoin assoc'])
        steps.extend(['dbjoin arrival'])
        steps.extend(['dbjoin snetsta'])

    else:
        steps = ['dbopen arrival']

    if start: steps.extend(['dbsubset time > %s' % start ])
    if end: steps.extend(['dbsubset time < %s' % end ])

    if subset: steps.extend(['dbsubset %s' % subset ])

    log( steps )

    with datascope.freeing(db.process( steps )) as dbview:
        for temp in dbview.iter_record():
            (snet,sta,chan,time,phase) = temp.getv('snet','sta','chan','arrival.time','arrival.iphase')

            if time < min_a: min_a = time
            if time > max_a: max_a = time
            sta = "%s_%s" % (snet,sta)

            if not sta in arrivals:
                arrivals[sta] = {}
            if not chan in arrivals[sta]:
                arrivals[sta][chan] = []
            arrivals[sta][chan].append( (time,phase) )
            log( "arrival %s %s = %s-%s" % (sta,chan,time,phase) )

    return (arrivals,min_a,max_a)

def get_sites(db,start,end,event=False,arrivals=False):
    '''
    Get the distance from every
    station to event
    '''
    if event:
        e_lat=event['lat']
        e_lon=event['lon']
    else:
        e_lat = False
        e_lon = False

    locations = {}
    start = stock.epoch2str(start, '%Y%j')
    end = stock.epoch2str(end, '%Y%j')

    steps = ['dbopen site']
    steps.extend(['dbjoin snetsta'])
    steps.extend(['dbsubset ondate <= %s && (offdate >= %s || offdate == NULL)' % (start,end)])
    steps.extend(['dbsort snet sta'])

    with datascope.freeing(db.process( steps )) as dbview:
        for temp in dbview.iter_record():
            if e_lat and e_lon:
                d = temp.ex_eval('distance(lat,lon,%s,%s)' % (e_lat,e_lon) )
            else:
                d = temp.record
            snet = temp.getv('snet')[0]
            sta = temp.getv('sta')[0]
            v = '%s_%s' % (snet,sta)
            if arrivals:
                if not v in arrivals: continue
            locations[v] = d
            log('site: %s distance: %s' % (sta,d) )

    return sorted(locations.items(), key=lambda x: x[1], reverse=True)

def get_event(db,evid):

    results = {}

    event_table = db.lookup(table='event')
    log('event table present: %s' % event_table.query(datascope.dbTABLE_PRESENT) )

    if event_table.query(datascope.dbTABLE_PRESENT):
        steps = ['dbopen event']
        steps.extend(['dbjoin origin'])
        steps.extend(['dbsubset evid==%s && prefor==orid' % evid])
    else:
        steps = ['dbopen origin']
        steps.extend(['dbsubset orid==%s' % evid ])

    log( steps )

    with datascope.freeing(db.process( steps )) as dbview:
        notify( 'Found (%s) events with id [%s]' % (dbview.record_count,evid) )

        if not dbview.record_count:
            # This failed. Lets see what we have in the db
            error('This failed. No events after subset.')

        #we should only have 1 here
        for temp in dbview.iter_record():

            (orid,time,lat,lon) = temp.getv('orid','time','lat','lon')

            log( "evid=%s orid=%s" % (evid,orid) )
            log( "time:%s (%s,%s)" % (time,lat,lon) )
            results['orid'] = orid
            results['time'] = time
            results['lat'] = lat
            results['lon'] = lon

    log(results)
    return results


usage = '\nUSAGE:\n\t%s [-v] [-m  20] [-o] [-a] [-i] [-j value] [-p pf] [-n ./output_file] [-f filter] [-e event_id] [-s wfdisc_subset_regex] db [start [end]] \n\n' % __file__


parser = OptionParser()
parser.add_option("-v",  dest="verbose", help="Verbose output",
                    action="store_true",default=False)
parser.add_option("-f", dest="filter", help="Filter data. ie. 'BW 0.1 4 3 4'",
                    action="store",default='')
parser.add_option("-a", dest="arrivals", help="Plot arrivals on traces.",
                    action="store_true",default=False)
parser.add_option("-i", dest="include", help="Include all arrivals on window.",
                    action="store_true",default=False)
parser.add_option("-o", dest="arrivals_only", help="Plot traces with arrivals only.",
                    action="store_true",default=False)
parser.add_option("-s", dest="subset", help="Subset. ie. 'sta=~/AAK/ && chan=~/.*Z/'",
                    action="store",default=None)
parser.add_option("-e", dest="event_id", help="Plot traces for event: evid/orid",
                    action="store",default=None)
parser.add_option("-p", dest="pf", help="Parameter File to use.",
                    action="store",default='plot_traces.pf')
parser.add_option("-m", dest="maxtraces", help="Don't plot more than this number of traces",
                    action="store", type='int', default=50)
parser.add_option("-n", dest="filename",
                    help="Save final plot to the provided name. ie. test.jpg",
                    action="store",default=None)
parser.add_option("-d", dest="display",
                    help="If saving to file then use -d to force image to open at the end.",
                    action="store_true",default=False)
parser.add_option("-j", dest="jump", type="int",
                    help="Avoid plotting every trace of the subset. Only use every N trace.",
                    action="store",default=1)


(options, args) = parser.parse_args()

if len(args) < 1 or len(args) > 3:
    parser.print_help()
    error(usage)

database = os.path.abspath(args[0])
start = False
end = False
if len(args) > 1: start = stock.str2epoch(args[1])
if len(args) > 2: end = stock.str2epoch(args[2])

# Verbose output?
if options.verbose:
    logger.setLevel(logging.INFO)

if options.filename:
    options.filename = os.path.abspath(options.filename)

log('database = %s' % database)
log('start = %s' % start)
log('end = %s' % end)

(tableau20, bg_color, figsize, timeformat, line_w, timewindow, add_shadow) = \
                                            get_pf_params(options.pf)

log('plot time window = [%s,%s]' % (start,end) )
# Get db ready
try:
    db = datascope.dbopen( database, "r" )
except Exception as e:
    error('Problems opening database: %s %s' % (database,e) )

# Extract event info if needed
if options.event_id:
    event = get_event(db,options.event_id)
    # Maybe we need to set our time here
    if not start: start = event['time'] - timewindow[0]
    if not end: end = event['time'] + timewindow[1]

else:
    event = False
    # Missing start or end times?
    if not start: start =  stock.now() - (timewindow[0] + timewindow[1])
    if not end: end = start + timewindow[1]

# Extract all arrivals for this event
arrivals = {}
if options.arrivals:
    if options.event_id:
        (arrivals,min_a,max_a) = \
                get_arrivals(db,event=options.event_id,subset=options.subset)

        if options.include:
            # Forced all flags into plot
            if min_a < start: start = min_a - 30
            if max_a > end: end = max_a + 30
    else:
        (arrivals,min_a,max_a) = \
                get_arrivals(db,start,end,subset=options.subset)

# Get distace to event if needed. Order stations by name otherwise
# Comes back as list of touples in reversed order
if options.arrivals_only:
    sites = get_sites(db,start,end,event,arrivals)
else:
    sites = get_sites(db,start,end,event)

log('plot time window = [%s,%s]' % (start,end) )

#Verify that we have what we need.
if not start:
    error("\nMissing start time: %s \n" % start)
if not end:
    error("\nMissing end time: %s \n" % end)

if start > stock.now() or start < 0:
    error("\nProblem with start time: %s => %s\n" % (args[1],start))
if end > stock.now() or end < 0:
    error("\nProblem with end time: %s => %s\n" % (args[2],end))

if options.filename:
    if not re.match('.*\.(jpg|eps|ps|pdf|svg)$',options.filename):
        error('\nOnly these types of images are permited: jpg, pdf, ps, eps and svg.\n')


# Get traces from wfdisc
(stations,total_traces) = extract_data(db,start,end,sites,subset=options.subset)

# Set text size base on total traces
text_size = 20
if total_traces > 30: text_size *= 0.75
if total_traces > 50: text_size *= 0.5
log( 'Text size: %s' % text_size )

# Create figure, extract axx to help with shadows
figure = plt.figure(figsize=figsize)
axx = figure.add_subplot(111)

color_count = 0
y_top_limit = 0
log( 'START PLOT:' )

# "sites" is inverted so we plot in order.
for sta,distance in sites:
    if not sta in stations: continue
    log( sta )

    color = tableau20[color_count%len(tableau20)]
    color_count += 1

    for chan in reversed(sorted(stations[sta])):
        name = "%s_%s" % (sta,chan)

        try:
            t = stations[sta][chan][0]
            d = stations[sta][chan][1]
        except:
            continue

        if not len(t) or not len(d): continue

        # Fix y values for the location on the canvas
        d += y_top_limit

        # plot trace
        log( '\t%s' % name )
        newline, = plt.plot(t,d,lw=line_w,color=color,zorder=2)

        if add_shadow:
            # plot some shadows
            dx, dy = 2/60., -2/60.
            offset = transforms.ScaledTranslation(dx, dy, figure.dpi_scale_trans)
            shadow_transform = axx.transData + offset
            plt.plot(t, d, lw=line_w, color='lightgray', transform=shadow_transform,
                            zorder=0.5*newline.get_zorder())

        # add name of trace with shadow

        # THIS METHOD WILL PUT THE NAME IN THE MIDDLE OF TRACE
        #y = ( ( max(d) - min(d) )/ 2 ) + min(d)
        # WE WANT THE NAME ON TOP OF THAT. LIKE 80% TO THE TOP.
        y = ( ( max(d) - min(d) ) * 0.8 ) + min(d)

        if add_shadow:
            text = plt.text(start, y, name, fontsize=text_size,
                    color=color,zorder=8)
            textshadow = plt.text(start, y, name, fontsize=text_size,
                    bbox=dict(edgecolor=bg_color, facecolor=bg_color, boxstyle='round,pad=0.2'),
                    color='lightgray',transform=shadow_transform,zorder=0.5*text.get_zorder())
        else:
            text = plt.text(start, y, name, fontsize=text_size,color=color,zorder=8,
                    bbox=dict(edgecolor=bg_color, facecolor=bg_color, boxstyle='round,pad=0.2'))


        # Track location on canvas
        y_top_limit += 1

        # Try to plot some arrivals
        try:
            for a in arrivals[sta][chan]:
                log('\t\tadd arrival: %s %s' % a)
                plt.plot([a[0],a[0]],[min(d)-0.15,max(d)-0.15],
                        color='red',lw=0.5)
                plt.text(a[0], max(d)-0.15, a[1], fontsize=text_size/2,
                        color=bg_color,bbox=dict(edgecolor='red', facecolor='red'))
        except:
            pass

# Set limits on our x-axis and y-axis
if y_top_limit: plt.ylim(0,y_top_limit)
plt.xlim([start,end])

# Extract some variables to help us modify
# the plot
x1,x2,y1,y2 = plt.axis()
ax = plt.gca()
pl = plt.gcf()

# Set background color
pl.set_facecolor(bg_color)
ax.patch.set_facecolor(bg_color)

# Remove outside border of figure
pl.tight_layout(pad=0)

# No outer frame
ax.spines["top"].set_visible(False)
ax.spines["bottom"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.spines["left"].set_visible(False)

# Remove all y ticks
ax.get_yaxis().set_ticks([])

# Set doted vertigal grid on plot
for x in ax.xaxis.get_ticklocs():
    plt.plot([x,x],[y1,y2], "--", lw=0.5, color="b", alpha=0.3)

# Plot new time ticks
x_ax = [stock.epoch2str(y,timeformat) for y in ax.xaxis.get_ticklocs()]
ax.set_xticklabels(x_ax,fontsize=10,y=0.02,bbox=dict(edgecolor=bg_color, facecolor=bg_color))


#" Set the title of the plot."
#text = '%s [%s,%s]   ' % (database,sta,chan)
#if options.filter:
#    text += ' filter:"%s"' % options.filter
#else:
#    text += ' filter:"NONE"'
#
#plt.title(text)

" Save plot and/or open final file. "
if options.filename:
    log( 'Save plot to: %s' % options.filename )
    plt.savefig(options.filename,bbox_inches='tight', facecolor=pl.get_facecolor(), edgecolor='none',pad_inches=0.5,dpi=200)
    if options.display: os.system( "open %s" % options.filename )
else:
    plt.show()
