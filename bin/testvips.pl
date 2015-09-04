#!/usr/bin/perl

##########################################################################
# Tests connectivity to the Core Mail Processor on each instance via the #
# instance VIPs. By default, tries all the VIPs, and then prints a       #
# summary of what failed. Pass -v to get more information about          #
# failures, and -vv to be even more verbose. If you just want an exit    #
# status, use -q.                                                        #
##########################################################################

use strict;
use warnings;
use Socket;

my @vips = (
    "ap0-cmp1-0-tyo.data.sfdc.net",
    "ap1-cmp1-0-tyo.data.sfdc.net",
    "ap2-cmp1-0-tyo.data.sfdc.net",
    "cs1-cmp1-0-sjl.data.sfdc.net",
    "cs2-cmp1-0-asg.data.sfdc.net",
    "cs3-cmp1-0-sjl.data.sfdc.net",
    "cs4-cmp1-0-asg.data.sfdc.net",
    "cs5-cmp1-0-tyo.data.sfdc.net",
    "cs6-cmp1-0-tyo.data.sfdc.net",
    "cs7-cmp1-0-chi.data.sfdc.net",
    "cs8-cmp1-0-chi.data.sfdc.net",
    "cs9-cmp1-0-was.data.sfdc.net",
    "cs10-cmp1-0-was.data.sfdc.net",
    "cs11-cmp1-0-was.data.sfdc.net",
    "cs12-cmp1-0-sjl.data.sfdc.net",
    "cs13-cmp1-0-asg.data.sfdc.net",
    "cs14-cmp1-0-chi.data.sfdc.net",
    "cs15-cmp1-0-chi.data.sfdc.net",
    "cs16-cmp1-0-chi.data.sfdc.net",
    "cs17-cmp1-0-was.data.sfdc.net",
    "cs18-cmp1-0-was.data.sfdc.net",
    "cs19-cmp1-0-chi.data.sfdc.net",
    "cs20-cmp1-0-was.data.sfdc.net",
    "cs21-cmp1-0-was.data.sfdc.net",
    "cs22-cmp1-0-was.data.sfdc.net",
    "cs23-cmp1-0-chi.data.sfdc.net",
    "cs24-cmp1-0-chi.data.sfdc.net",
    "cs25-cmp1-0-chi.data.sfdc.net",
    "cs26-cmp1-0-was.data.sfdc.net",
    "cs28-cmp1-0-chi.data.sfdc.net",
    "cs30-cmp1-0-sjl.data.sfdc.net",
    "cs31-cmp1-0-tyo.data.sfdc.net",
    "cs32-cmp1-0-wax.data.sfdc.net",
    "cs33-cmp1-0-wax.data.sfdc.net",
    "cs40-cmp1-0-chi.data.sfdc.net",
    "cs41-cmp1-0-was.data.sfdc.net",
    "cs42-cmp1-0-chi.data.sfdc.net",
    "cs43-cmp1-0-was.data.sfdc.net",
    "cs80-cmp1-0-lon.data.sfdc.net",
    "cs81-cmp1-0-lon.data.sfdc.net",
    "eu0-cmp1-0-was.data.sfdc.net",
    "eu1-cmp1-0-chi.data.sfdc.net",
    "eu2-cmp1-0-was.data.sfdc.net",
    "eu3-cmp1-0-was.data.sfdc.net",
    "eu5-cmp1-0-lon.data.sfdc.net",
    "na0-cmp1-0-asg.data.sfdc.net",
    "na1-cmp1-0-sjl.data.sfdc.net",
    "na2-cmp1-0-chi.data.sfdc.net",
    "na3-cmp1-0-asg.data.sfdc.net",
    "na4-cmp1-0-was.data.sfdc.net",
    "na5-cmp1-0-chi.data.sfdc.net",
    "na6-cmp1-0-sjl.data.sfdc.net",
    "na7-cmp1-0-was.data.sfdc.net",
    "na8-cmp1-0-chi.data.sfdc.net",
    "na9-cmp1-0-chi.data.sfdc.net",
    "na10-cmp1-0-chi.data.sfdc.net",
    "na11-cmp1-0-was.data.sfdc.net",
    "na12-cmp1-0-was.data.sfdc.net",
    "na13-cmp1-0-chi.data.sfdc.net",
    "na14-cmp1-0-was.data.sfdc.net",
    "na15-cmp1-0-chi.data.sfdc.net",
    "na16-cmp1-0-was.data.sfdc.net",
    "na17-cmp1-0-was.data.sfdc.net",
    "na18-cmp1-0-was.data.sfdc.net",
    "na19-cmp1-0-chi.data.sfdc.net",
    "na20-cmp1-0-chi.data.sfdc.net",
    "na21-cmp1-0-wax.data.sfdc.net",
    "na22-cmp1-0-was.data.sfdc.net",
    "na23-cmp1-0-was.data.sfdc.net",
    "na24-cmp1-0-was.data.sfdc.net",
    "na26-cmp1-0-was.data.sfdc.net",
    "na27-cmp1-0-chi.data.sfdc.net",
    "na29-cmp1-0-chi.data.sfdc.net",
    "na41-cmp1-0-was.data.sfdc.net",
    "gs0-cmp1-0-chi.data.sfdc.net",
);

my $loglevel = 3;
for my $arg (@ARGV) {
    if ($arg eq "-q") {
        $loglevel = 5;
    } elsif ($arg =~ /-v+/) {
        $loglevel -= (length($arg) - 1);
    } else {
        usage();
    }

}

sub logme {
    my $level = shift;
    my $message = shift;
    if ($level >= $loglevel) {
        print "$message\n";
    }
}

sub err {
    logme 2, shift();
}

sub info {
    logme 1, shift();
}

sub result {
    logme 3, shift();
}

sub test_vip {
    my $vip = shift;
    my $iaddr = inet_aton($vip);
    if (! $iaddr) {
        err "Could not resolve $vip.";
        return 0;
    }
    my $paddr = sockaddr_in(2525, $iaddr);
    my $proto = getprotobyname('tcp');
    my $in;
    info "Testing $vip";
    my $success = socket($in, PF_INET, SOCK_STREAM, $proto);
    if (! $success) {
        err "failed to create socket: $!";
        return 0;
    }
    $success = connect($in, $paddr);
    if (! $success) {
        err "failed to connect to $vip: $!";
        return 0;
    }
    my $rv = 0;
    if (chomp(my $line = <$in>)) {
        if ($line =~ /^220 /) {
            info "Got banner from $vip: $line";
            $rv = 1;
        } else {
            err "No banner from $vip. Got: $line";
        }
    } else {
        err "No banner from $vip: $!";
    }
    close $in;
    info "";
    return $rv;
}

my @badvips;
for my $vip (@vips) {
    if (! test_vip($vip)) {
        push @badvips, $vip;
    }
}

err "";
if (@badvips) {
    result "The following vips failed (". scalar(@badvips) .  " out of " . scalar(@vips) . "):";
    result join("\n", @badvips);
    exit 1;
} else {
    result "All OK. " . scalar(@vips) . " tested.";
}

sub usage {
    print STDERR <<END;

Usage: testvips.pl [ -q | -v | -vv ]

Description:
    Attempts to connect to CMP on each instance (via the instance
    VIPs), and then prints a summary of what failed. Exits with
    nonzero status if there are any failures.

Options:

  -v  Print more information about failures
  -vv Print information about connection attempts
  -q  Print nothing
  -h  Print this help and exit

END
;
    exit 1;
}