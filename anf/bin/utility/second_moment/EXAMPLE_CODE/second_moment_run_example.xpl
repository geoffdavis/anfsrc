#   Copyright (c) 2016 Boulder Real Time Technologies, Inc.
#
#   Written by Rebecca Rodd
#
#   This software may be used freely in any way as long as
#   the copyright statement above is not removed.

use Cwd;
use Datascope ;
use File::Path;

#
# SIMPLE SCRIPT TO RUN DEMO CODE FOR SECOND_MOMENT
#

$path = "$ENV{ANF}/example/second_moment";
$need_link = 0;

print "\nRUN SECOND_MOMENT DEMO\n";


# TEST FOR GLOBAL SETTINGS
if ( exists($ENV{ANF}) ) {
    print "\nANTELOPE VERSION: $ENV{ANF}\n" ;
} else {
    die "\nNO ANTELOPE CONFIGURED IN ENVIRONMENT\n" ;
}

# ALTERNATIVE DIRECTORY TO USE FOR TEST
if ( scalar @ARGV ) {
    $path = abspath($ARGV[0]) ;
    $need_link = 1 ;
    makedir($path) unless -d $path ;
}


# TEST FOR EXAMPLE DIRECTORY
#die "\nNO DIRECTORY FOR EXAMPLE: [$path]\n"  unless -d $path;


# GO TO DIR
print "\nCHANGE TO DIRECTORY: [$path]\n";
chdir $path or die "Could not change to directory '$path' $!";


# CLEAN DIRECTORY
foreach ( "path/.second_moment", "$path/second_moment_images") {
    if ( -e $_ ) {
        print "\nREMOVE TEMP FOLDER: [$_]\n";
        rmtree $_;
    }
}


# RUN EXAMPLES
foreach (1) {
    print "\nSTART EXAMPLE $_\n";
    print "\nsecond_moment -v --fault '307,83,217,82' EXAMPLE_$_/example_$_ 1\n";
    $return_value = system( "second_moment -v --fault '307,83,217,82' EXAMPLE_$_/example_$_ 1" );

    print "\nDONE WITH EXAMPLE $_\n";
}


print "\nDONE SECOND_MOMENT DEMO!\n";
