
#
#   baler44_uploaded: script to migrate data from baler44 files uploaded to ANF
#   author: Juan C. Reyes
#   email:  reyes@ucsd.edu
#   No BRTT support
#

use archive ;
use sysinfo ;
use Datascope ;
use Pod::Usage "pod2usage" ;
use Getopt::Std "getopts" ;
use File::Copy "move" ;
use File::Path "make_path" ;


#
#  Program setup
#
    $start = now() ;
    $parent = $$ ;

    if ( ! getopts('vnhm:d:') || @ARGV != 2 ) {
        pod2usage({-exitval => 2, -verbose => 2}) ;
    }

    pod2usage({-exitval => 2, -verbose => 2}) if $opt_h ;

    savemail() if $opt_m ;

    elog_init($0,@ARGV) ;

    elog_notify('') ;
    elog_notify("$0 @ARGV") ;
    elog_notify("Starting execution at "
                .strydtime($start)." on ".my_hostname()) ;
    elog_notify('') ;
    elog_notify('') ;

    $source = $ARGV[0] ;
    $target = $ARGV[1] ;
    #$source = "/anf/TA/baler/www_uploaded_files" ;
    #$target = "/anf/TA/baler/work" ;

    elogdie("[$source] not a folder") unless -d $source ;
    elogdie("[$target] not a folder") unless -d $target ;

    #
    # Read source directory
    #
    @stations = read_dir( $source ) ;

    #
    # Read target directory
    #
    @archives = read_dir( $target ) ;


    if ( $opt_v ) {

        elog_notify("Folders in source directory: [$source]") ;

        if (scalar @stations > 0 ) {
            elog_notify("\t$source/$_") foreach sort @stations ;
            #elog_notify("\t[@stations]") foreach sort @stations ;
        } else {
            elog_notify("\t*** EMPTY ***") ;
        }

        #elog_notify("Folders in target directory: [$target]") ;
        #elog_notify("\t$target/$_") foreach sort @archives ;
    }

    unless (scalar @stations > 0 ){
        elog_notify("Source[$source] folder is empty.") ;
        elog_notify("Nothing to do!") ;
        sendmail("baler44_uploaded: No files",$opt_m) if $opt_m ;
        exit ;
    }

    elogdie("[$target] folder is empty!") unless scalar @archives > 0 ;

    #
    #  Main
    #
    foreach my $sta (sort @stations) {
        elog_notify("") ;
        elog_notify("Working with station: [$sta]") ;

        #
        # Verify we have a folder
        #
        my $source_sta = "$source/$sta" ;
        elog_notify("Source directory: [$source_sta]") ;
        unless ( -d $source_sta ) {

            elog_complain("") ;
            elog_complain("ERROR: [$source_sta] is not a folder.") ;
            elog_complain("ERROR: This will need manual removal.") ;
            elog_complain("") ;
	    $iserror++ ; 
            next ;

        }

	# 
	# Confirm no new data is currently being uploaded
	#  (default is data must be older than one day
	#
	

	my $ok_diff = $opt_d ? $opt_d : 86400   ;

        my $time_diff = now() - (stat ("$source/$sta"))[9] ;


	elog_notify("Checking that upload directory has no data updated within $ok_diff seconds") ;

	if ( $time_diff  < $ok_diff) {
	    elog_complain ("ERROR: Data available is newer than allowed for processing.") ;
	    elog_complain ("ERROR: Skipping $sta processing.") ;
	    elog_complain ("Timediff is only: $time_diff") if $opt_v ;
	    $iserror++ ; 
	    next; 
	} else { 
	    elog_notify ("Data is older than wait time.") if $opt_v ;
	} 

	

        #
        # Verify station source folder
        #
        @files = read_dir( $source_sta ) ;

        unless ( scalar @files > 0 ) {

            elog_complain("") ;
            elog_complain("Folder for station [$sta] is empty!.") ;
            rm_dir($source_sta) ;
            elog_complain("") ;
	    $iserror++ ; 
            next ;

        }

        #
        # Verify station target folder
        #
        my $target_sta = "$target/$sta" ;
        my $target_md5 = "$target_sta/md5" ;
        if ( -d $target_sta ) {

            #
            # Got folder. Now verify station md5 folder
            #
            unless ( -d $target_md5 ) {

                elog_complain("") ;
                elog_complain("ERROR: Cannot find [$target_md5].") ;
                elog_complain("Create folder [$target_md5]") ;
                elog_complain("") ;
                mk_dir( $target_md5 ) ;

            }

        } else {

            #
            # If there  is no folder then...
            #
            elog_complain("") ;
            elog_complain("ERROR: Cannot find [$target_sta].") ;

            #
            # We don't want to create a folder for the station.
            # Use a temp folder in the target directory.
            #
            $target_sta = "$target/temp" ;
            $target_md5 = "$target/temp" ;
            elog_complain("Create temp folder [$target_sta]") ;
            elog_complain("") ;
            mk_dir( $target_sta ) ;

        }


        #
        # Move md5 files
        #
        opendir $temp, $source_sta
            or elogdie("Cannot open dir [$source_sta]: $!") ;

        #
        # Grab every file in the
        # upload directory.
        #
        foreach (readdir $temp){

            next if /^\.\.?$/ ;
            if (/.*\.md5/){

                #elog_notify("mv_file $source_sta/$_,$target_md5/$_") ;
                mv_file("$source_sta/$_","$target_md5/$_") ;

                if ( -f "$target_md5/$_" ) {
                    elog_notify("[$target_md5/$_] verified");
                } else {
                    elog_complain("ERROR: Cannot verify [$target_md5/$_]") ;
                }

            } else {

                #elog_notify("mv_file $source_sta/$_,$target_sta/$_") ;
                mv_file("$source_sta/$_","$target_sta/$_") ;

                if ( -f "$target_sta/$_" ) {
                    elog_notify("[$target_sta/$_] verified");
                } else {
                    elog_complain("ERROR: Cannot verify [$target_sta/$_]") ;
                }

            }
        }
        closedir $temp ;

        #
        # Remove source folder
        #
        elog_notify("Done with folder [$sta]") if $opt_v ;
        elog_notify("Remove source directory [$source_sta]") if $opt_v ;
        rm_dir($source_sta) ;
    }

    $end = now() ;
    $run_time_str = strtdelta($end - $start) ;
    $start = strydtime($start) ;
    $end = strydtime($end) ;

    if ( $opt_v ) {
        elog_notify("\n\n----------------- END -----------------\n\n") ;
        elog_notify("Start: $start End: $end") ;
        elog_notify("Runtime: $run_time_str") ;
    }

    if ($opt_m) {
	if ($iserror) { 
	    sendmail("baler44_uploaded: ERROR",$opt_m) if $opt_m ;
	} else { 
	    sendmail("baler44_uploaded: Successful upload",$opt_m) if $opt_m ;
	}
    } else {
	if ($iserror) {
	    elog_notify("Some problems with upload");
	} else {
	    elog_notify("Sucessful upload");
	}
    }

    exit ;


sub read_dir {
    #
    # Read source directory
    #

    $dir = shift ;
    my $temp ;
    my @stations ;

    opendir $temp, $dir or elogdie("Couldn't open dir '$source': $!") ;

    foreach (readdir $temp){
        next if /^\.\.?$/ ;
        push @stations,$_ ;
    }

    closedir $temp ;

    return @stations ;
}

sub mk_dir {
    #
    # Build the directory structure needed.
    #
    my $dir = shift ;

    if ( $opt_v ) {
        elog_notify("") ;
        elog_notify("Make directory: $dir") ;
        elog_notify("") ;
    }

    unless ( $opt_n ) {
      if ( !-d $dir ) { 
        make_path($dir) or elogdie("Cannot make directory [$dir]: $!") ;
      } else {
        elog_notify("Directory already exists: $dir") ;
      }

    }

    return ;

}

sub mv_file {
    #
    # Move a file from one
    # directory to another.
    #
    my ($old_file,$new_file) = @_ ;
    my @path;
    my ($filename, $basedir );

    if ( $opt_v ) {
        elog_notify("") ;
        elog_notify("move: $old_file => $new_file") ;
        elog_notify("") ;
    }

    unless ( $opt_n ) {


        #
        # If we have a copy of the old file then
        # we send that to trash.
        #
        if ( -f $new_file ) {
            @path = split(/\//, $new_file);
            $filename = pop @path;
            pop @path if $path[-1] =~ /md5/;
            $basedir = join( '/', @path );
            elog_notify("Need to remove previous file: $_ to $basedir/trash/$filname") ;
            move($new_file,"$basedir/trash/$filename")
                or elogdie("ERROR: move [$new_file -> $basedir/trash/]: $!") ;
        }

        move($old_file,$new_file)
            or elogdie("ERROR: move [$old_file -> $new_file]: $!") ;

    }

    return ;

}

sub rm_dir {
    #
    # Clean the archive of folders
    # at the end of the run.
    #
    my $dir = shift ;

    if ( $opt_v ) {
        elog_notify("") ;
        elog_notify("Remove: $dir") ;
        elog_notify("") ;
    }

    unless ( $opt_n ) {
        rmdir $dir or elogdie("Cannot remove directory [$dir]: $!") ;

    }

    return ;

}

sub elogdie {
    #
    # Wrapping elog_die with a
    # method to email log before
    # quitting.
    #
    my $msg = shift ;

    elog_complain("ERROR: Call to elog_die().") ;
    elog_complain($msg) ;

    sendmail("baler44_uploaded: ERROR",$opt_m) if $opt_m ;

    elog_die($msg) ;

}



__END__



=pod

=head1 NAME

baler44_uploaded - automatic uplaod of Baler44 files

=head1 SYNOPSIS

baler44_uploaded [-h] [-n] [-v] [-m email] [-d seconds] source_dir target_dir 

=head1 SUPORT

No BRTT support == contact Juan Reyes <reyes@ucsd.edu>

=head1 ARGUMENTS

Recognized flags:

=over 2

=item B<-h> 

Produce this documentation

=item B<-n> 

Test  mode/dry  run.  Does not delete, copy or move  any file or folder.

=item B<-v> 

Produce detailed logs 

=item B<-m emails> 

List of emails to send logs.

=item B<-d seconds>> 

Delay time in seconds between last modification time of upload directory 
and current time.  If there are files modified more recently than this,
processing for that station will be skipped.  The default delay if this
is not specified, is one day (86400 seconds).

=back

=head1 DESCRIPTION

baler44_uploaded  migrates  files  from the remote uploads to permanent
archives.  Designed to run out of crontab and email results.  The script
will  list  files in the source directory and then migrate the data to the
target directory. The source directory gets data from the automatic
uplaod GUI run by AOF/AOC and a PHP script at anf.ucsd.edu saves
the data in a temp folder.

The script will start reading the source directory and moving each file
into its station  directory of the target directory.  If the folder is
missing the script will create one. If the folder for the checksums is
missing the scirpt will create a folder "md5" inside the target direc-
tory.

The assumptions of the program are that:

    The source directory is one level deep and include folders  with
    the names of the stations.

    Every file for the station is in the station folder. No matching
    for station name is performed at this time.  That  was  done  at
    uplaod time.

=head1 ENVIRONMENT

needs to have sourced $ANTELOPE/setup.csh.

=head1 AUTHOR

Juan C. Reyes <reyes@ucsd.edu>

=head1 SEE ALSO

Perl(1).

=cut
#}}}
