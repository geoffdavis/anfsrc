#!/opt/antelope/current/bin/perl

use lib "/opt/antelope/current/data/perl" ;
require 'cgi-lib.pl';

$registrydb="~rt/db/ucsd_orbregistry";

use orb;
use Datascope;
use Socket;

$match="";
&ReadParse;

%matchhash;

if (defined $in{"match"})
{
    $match=$in{"match"};
    $match =~ s/\%2F/\//g;
    $match =~ s/\%5C/\\/g;
    $match =~ s/\\\//\//g;
    $match2=$match;
    $match =~ s/\//\\\//g;

    foreach $i (`/opt/antelope/current/bin/dbsubset $registrydb.sources "srcname=~/$match/" | /opt/antelope/current/bin/dbselect - serveraddress serverport nbytes`)
    { 
        my ($serveraddress,$serverport,$nbytes)=split /\s+/, $i;
	if (defined $matchhash{"$serveraddress:$serverport"})
	{
	    $matchhash{"$serveraddress:$serverport"}++;
	    $matchbytes{"$serveraddress:$serverport"}+=$nbytes;
	}
	else
	{
	    $matchhash{"$serveraddress:$serverport"}=1;
	    $matchbytes{"$serveraddress:$serverport"}=$nbytes;
	}
	    
    }
}

$twin=now()-6*60*60;

foreach $i (`/opt/antelope/current/bin/dbsubset $registrydb.connections "when >= '$twin'" | /opt/antelope/current/bin/dbselect - fromaddress fromport toaddress toport latency_sec`)
{
    ($fromaddress,$fromport,$toaddress,$toport,$latency)=split /\s+/, $i;
    ($fromaddresso,$fromporto,$toaddresso,$toporto,$latencyo)=split /\s+/, $i;

    $srcnameip=$fromaddress;
    $srcnameip=inet_aton($srcnameip);
    $srcnameip=gethostbyaddr($srcnameip, AF_INET);
    if ($srcnameip ne "")
    { $fromaddress=$srcnameip; }

    $srcnameip=$toaddress;
    $srcnameip=inet_aton($srcnameip);
    $srcnameip=gethostbyaddr($srcnameip, AF_INET);
    if ($srcnameip ne "")
    { $toaddress=$srcnameip; }

    foreach $portname (`egrep \"\s*$fromport\s*\" /opt/antelope/current/data/pf/orbserver_names.pf`)
    {
	if ($portname =~ /\s+$fromport\s+/)
	{
	    ($fromport,$mold)=split /\s+/,$portname;
	}
    }

    foreach $portname (`egrep \"\s*$toport\s*\" /opt/antelope/current/data/pf/orbserver_names.pf`)
    {
	if ($portname =~ /\s+$toport\s+/)
	{
	    ($toport,$mold)=split /\s+/,$portname;
	}
    }

    $hosts{"$fromaddress:$fromport"}="$fromaddresso:$fromporto";
    $hosts{"$toaddress:$toport"}="$toaddresso:$toporto";
    $latency=strtdelta($latency);
    if ($match ne "")
    {
	$conn{"$fromaddress:$fromport->$toaddress:$toport"}="\"$fromaddress:$fromport\" -> \"$toaddress:$toport\" [color=blue, label=\"orb2orb\" href=\"orbtopo_detail.cgi?mode=connection&src=$fromaddress:$fromport&dest=$toaddress:$toport&match=$match\"]";
    }
    else
    {
	$conn{"$fromaddress:$fromport->$toaddress:$toport"}="\"$fromaddress:$fromport\" -> \"$toaddress:$toport\" [color=blue, label=\"$latency\" href=\"orbtopo_detail.cgi?mode=connection&src=$fromaddress:$fromport&dest=$toaddress:$toport&match=$match\"]";	
    }
}

#open(FOO,">/dev/stdout");
#syswrite FOO, "Content-type: image/gif\nPragma: no-cache\n\n";
#syswrite FOO, "Content-type: text/html\nPragma: no-cache\n\n";
#close(FOO);

open(FOO,"> /tmp/orbtopo.$$.dot");
print FOO "Digraph orbtopo {\n";
foreach $i (keys %hosts)
{
    ($ip,$port)=split /:/,$hosts{$i};
    if (defined $matchhash{"$ip:$port"})
    {
	$cnt=$matchhash{"$ip:$port"};
	if ($cnt>1)
	{
	    $cnt="$cnt srcs matches $match2";
	}
	else
	{
	    $cnt="$cnt src matches $match2";
	}
	$f=sprintf("\\nusing %.2f MB", $matchbytes{"$ip:$port"}/1024.0/1024.0);
	
	print FOO "\t\"$i\" [shape=hexagon,style=filled,fillcolor=green, label=\"$i\\n$cnt$f\", href=\"orbtopo_detail.cgi?mode=orb&orbname=$ip:$port&match=$match\"]\n";
    }
    else
    {
	$v=`/opt/antelope/current/bin/dbsubset ~rt/db/ucsd_orbregistry.servers "serveraddress=='$ip' && serverport=='$port' && when >= '$twin'" | /opt/antelope/current/bin/dbselect - maxdata`;
	chomp($v);
	if ($v>0)
	{
	    $f=sprintf("\\n%.2f MB Capacity", $v/1024.0/1024.0);
	}
	else
	{
	    $f="";
	}	
	print FOO "\t\"$i\" [shape=hexagon,style=filled,fillcolor=lightgoldenrod1, label=\"$i$f\", href=\"orbtopo_detail.cgi?mode=orb&orbname=$ip:$port&match=$match\"]\n";
    }
}
foreach $i (keys %conn)
{
    print FOO "\t";
    print FOO $conn{$i};
    print FOO "\n";
}
print FOO "}\n";
close(FOO);
`/usr/bin/dot -Tpng -o /var/Web/tmp/orbtopo.$$.png /tmp/orbtopo.$$.dot 2>/dev/null`;
$map=`/usr/bin/dot -Tcmapx -o /dev/stdout /tmp/orbtopo.$$.dot 2>/dev/null`;
print "Content-type: text/html\nPragma: no-cache\n\n";
print "<HTML><HEAD><TITLE>ORB Topo $match2</TITLE></HEAD>\n<BODY BGCOLOR=FFFFFF>";
if ($match ne "")
{
    print "<TABLE WIDTH=100%><TR><TD WIDTH=100%><CENTER><H1>ORB Topology Display for \"$match2\"</H1></CENTER>\n<HR></TD><TD ALIGN=RIGHT><A HREF=\"http://roadnet.ucsd.edu/\"><IMG SRC=\"http://roadnet.ucsd.edu/images/sub-sidebar_r13_c1.jpg\" WIDTH=156 HEIGHT=103 BORDER=0></A></TD></TR></TABLE>";
}
else
{
    print "<TABLE WIDTH=100%><TR><TD WIDTH=100%><CENTER><H1>ORB Topology Display</H1></CENTER>\n<HR></TD><TD ALIGN=RIGHT><A HREF=\"http://roadnet.ucsd.edu/\"><IMG SRC=\"http://roadnet.ucsd.edu/images/sub-sidebar_r13_c1.jpg\" WIDTH=156 HEIGHT=103 BORDER=0></A></TD></TR></TABLE>";
}
#print "<a href=\"/tmp/orbtopo.$$.cmapx\">";
print "<img src=\"/tmp/orbtopo.$$.png\" border=0 usemap=\"#orbtopo\" ismap>\n$map\n";
print "<FORM METHOD=GET ACTION=orbtopo.cgi>Highlight data matching regex: <INPUT TYPE=TEXT NAME=match VALUE=\"$match2\"></FORM>";
print "</BODY></HTML>\n";

unlink("/tmp/orbtopo.$$.dot");
