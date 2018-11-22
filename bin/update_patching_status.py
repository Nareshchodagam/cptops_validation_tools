#!/usr/bin/env python
#imports

from sys import exit
from subprocess import Popen, PIPE
from argparse import ArgumentParser
import logging


def update_iDB(cmd):
    """
    This function updates iDB entry
    :param cmd: command to run
    :return:
    """
    command = Popen([cmd], stdout=PIPE, shell=True)
    (output, _) = command.communicate()
    return output

def update_clusterconfig(clustername, status):
    """
    This function updates cluster config
    :param clustername: cluster name
    :param status: value of patching_inprogress
    :return:
    """
    cmd = "inventory-action.pl -use_krb_auth -resource cluster  -name "\
          + clustername + " -action read | egrep -i 'patching_inprogress|hbaseReleaseStatus' -A1"
    output = update_iDB(cmd)
    if 'complete' in output.lower():
        if status and 'false' in output.lower():
            logger.info("Updating cluster config patching_inprogress true for "
                            "cluster {0} ".format(clustername))
            value = "true"
        elif not status and 'true' in output.lower():
            logger.info("Updating cluster config patching_inprogress false for "
                            "cluster {0} ".format(clustername))
            value = "false"
        else:
            logger.info("Cluster config patching_inprogress is already updated for "
                            "cluster {0} ".format(clustername))
            logger.debug(output)
            value = None
        if value is not None:
            cmd = "inventory-action.pl -use_krb_auth -resource " \
                    "cluster -name " + clustername + " -action update -updateFields " \
                                                   "'clusterConfig.type=all,clusterConfig.key=patching_inprogress," \
                                                   "clusterConfig.value="+ value +"' | grep patching -A1"
            output = update_iDB(cmd)
            logger.info(output)
    elif 'complete' not in output.lower():
        logger.error("HbaseReleaseStatus is not COMPLETE")
    else:
        logger.error("Cluster config HbaseReleaseStatus|patching_inprogress not found")


def update_hostconfig(host, status):
    """
    This function updates host config
    :param host: hostname
    :param status: value of disable_host_alerts
    :return:
    """
    cmd = "inventory-action.pl -use_krb_auth -resource host -name "+ host +"  -action read | grep -w 'disable_host_alerts' -A1"
    output = update_iDB(cmd)
    if output:
        if status and 'false' in output.lower():
            logger.info("Updating host config disable_host_alerts true for host {0} ".format(host))
            value = "true"
        elif not status and 'true' in output.lower():
            logger.info("Updating host config disable_host_alerts false for host {0} ".format(host))
            value = "false"
        else:
            logger.info("Host config disable_host_alerts is already updated for host {0} ".format(host))
            logger.debug(output)
            value = None
        if value is not None:
            cmd = "inventory-action.pl -use_krb_auth -resource host -name" \
              " "+ host +" -action update -updateFields " \
                         "'hostConfig.applicationProfileName=hbase," \
                         "hostConfig.key=disable_host_alerts,hostConfig.value="+ value +"'| grep disable_host_alerts -A1"
            output = update_iDB(cmd)
            logger.info(output)
    else:
        logger.error("host config disable_host_alerts not found")

if __name__ == "__main__":

    parser = ArgumentParser(prog='update_patching_status.py',
                            usage='\n%(prog)s --start --host|--cluster'
                                  ' <hostname>|<clustername>\n%(prog)s --end --host <hostname> --cluster <clustername>')
    parser.add_argument("--start", "-s", dest="start", action="store_true", default=False,
                        help="To update patching progress in iDB")
    parser.add_argument("--host", dest="hostnames", help="HostNames")
    parser.add_argument("--cluster", dest="clusters", help="cluster name")
    parser.add_argument("--verbose", "-v", action="store_true", dest="verbose", default=False, help="verbosity")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    if args.hostnames:
        if not isinstance(args.hostnames, list):
            hosts = args.hostnames.split(',')
        else:
            hosts = args.hostnames
        for host in hosts:
            update_hostconfig(host, args.start)
    elif args.clusters:
        if not isinstance(args.clusters, list):
            cluster = args.clusters.split(',')
        else:
            cluster = args.clusters
        for clust in cluster:
            update_clusterconfig(clust, args.start)
    else:
        logger.error("hostname or clustername required")
