#!/usr/bin/env python
#imports

from sys import exit
from subprocess import Popen, PIPE, CalledProcessError
from argparse import ArgumentParser
import logging
from multiprocessing import Pool, cpu_count


def update_iDB(cmd):
    """
    This function updates iDB entry
    :param cmd: command to run
    :return:
    """
    try:
        command = Popen([cmd], stdout=PIPE, shell=True)
        (output, err) = command.communicate()
    except CalledProcessError as error:
        logger.error(error)
        exit(1)
    return output

def idb_command(is_cluster, name, action, value):
    """
    This function creates idb command
    :param is_cluster: true if name is cluster or false if name is host
    :param name: clustername | hostname
    :param action: read|update|create
    :param value: true or false
    :return: idb command
    """
    if is_cluster:
        if action == "read":
            cmd = "inventory-action.pl -use_krb_auth -resource cluster  -name "\
             + name + " -action "+ action +" | egrep -i 'patching_inprogress|hbaseReleaseStatus' -A1"
        else:
            cmd = "inventory-action.pl -use_krb_auth -resource " \
                    "cluster -name " + name + " -action "+ action +" -updateFields " \
                                                   "'clusterConfig.type=all,clusterConfig.key=patching_inprogress," \
                                                   "clusterConfig.value="+ value +"' | grep patching -A1"
    else:
        if action == "read":
            cmd = "inventory-action.pl -use_krb_auth -resource host -name "+ name +"  -action "+ action +" | grep -w 'disable_host_alerts' -A1"
        else:
            cmd = "inventory-action.pl -use_krb_auth -resource host -name" \
              " " + name + " -action "+ action +" -updateFields " \
                           "'hostConfig.applicationProfileName=hbase," \
                           "hostConfig.key=disable_host_alerts,hostConfig.value=" + value + "'| grep disable_host_alerts -A1"
    return cmd

def update_clusterconfig(clustername, status):
    """
    This function updates cluster config
    :param clustername: cluster name
    :param status: value of patching_inprogress
    :return:
    """
    is_cluster = True
    value = None
    action = "read"
    cmd = idb_command(is_cluster, clustername, action, value)
    output = update_iDB(cmd)
    if ('patching_inprogress' in output.lower() and 'hbasereleasestatus' in output.lower()):
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
        else:
            logger.error("HbaseReleaseStatus is not COMPLETE for cluster {0} ".format(clustername))
            raise Exception('known exception')
    else:
        logger.debug(output)
        logger.error("Cluster config HbaseReleaseStatus|patching_inprogress not found for cluster {0} ".format(clustername))
        logger.error("Contact Bigdata operations")
        raise Exception('known exception')
        # Update idb
    if value is not None:
        action = "update"
        cmd = idb_command(is_cluster, clustername, action, value)
        output = update_iDB(cmd)
        logger.info(output)


def update_clusterconfig_migration(clustername, start=False):
    """
    This function reads/updates centosMigrationInProgress field of a cluster
    :param clustername: cluster name
    :param start: Sets the field to True. Fetches the status of the field if this parameter is not passed.
    :return:
    """



    cmd = "inventory-action.pl -use_krb_auth -resource cluster  -name "\
         + clustername + " -action  read | egrep -i 'centosMigrationInProgress' -A1"
    output = update_iDB(cmd)

    if ('centosmigrationinprogress'in output.lower()):
        if 'true' in output.lower():
            logger.info("centosMigrationInProgress field is true for cluster {0}".format(clustername))
        else:
            logger.error("centosMigrationInProgress is False for cluster {0}. ".format(clustername))
            if start:

                cmd = 'inventory-action.pl -use_krb_auth -action update -resource cluster -name ' + clustername + \
                      ' -updateFields "clusterConfig.key=centosMigrationInProgress,clusterConfig.type=all,clusterConfig.value=true"'
                update_iDB(cmd)
                logger.info("Field is set to True now ")
            else:
                logger.error("Contact Bigdata operations(Uttam Kumar) to check for any ongoing releases  ".format(clustername))
                exit(1)
    else:
        logger.debug(output)
        logger.error("The field centosMigrationInProgress not found for cluster {0} ".format(clustername))
        logger.error("Contact Bigdata operations(Uttam Kumar)")
        raise Exception('known exception')
        # Update idb



def update_hostconfig(host, status):
    """
    This function updates host config
    :param host: hostname
    :param status: value of disable_host_alerts
    :return:
    """
    is_cluster = False
    value = None
    action = "read"
    cmd = idb_command(is_cluster, host, action, value)
    output = update_iDB(cmd)
    if output:
        action = "update"
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
    else:
        value = "true" if status else "false"
        action = "create"
    # update idb
    if value is not None:
        cmd = idb_command(is_cluster, host, action, value)
        output = update_iDB(cmd)
        logger.info(output)

if __name__ == "__main__":

    parser = ArgumentParser(prog='update_patching_status.py',
                            usage='\n%(prog)s --start --host|cluster'
                                  ' <hostname>|<clustername>\n%(prog)s --host|cluster <hostname>|<clustername>')
    parser.add_argument("--start", "-s", dest="start", action="store_true", default=False,
                        help="Update patching progress in iDB")
    parser.add_argument("--host", dest="hostnames", help="Host name")
    parser.add_argument("--cluster", dest="clusters", help="cluster name")
    parser.add_argument("--verbose", "-v", action="store_true", dest="verbose", default=False, help="verbosity")
    parser.add_argument("--migration", "-m", dest="migration", action="store_true", default=False,
                        help="Update/check Migration progress in iDB")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    processes = cpu_count()
    pool = Pool(processes)
    if args.hostnames:
        if not isinstance(args.hostnames, list):
            hosts = args.hostnames.split(',')
        else:
            hosts = args.hostnames
        _ = [pool.apply(update_hostconfig, args=(host, args.start)) for host in hosts]
    elif args.clusters:
        if not isinstance(args.clusters, list):
            cluster = args.clusters.split(',')
        else:
            cluster = args.clusters
        if args.migration:
            update_clusterconfig_migration(args.clusters, args.start)
        else:
            try:
                _ = [pool.apply(update_clusterconfig, args=(clust, args.start, args.migration)) for clust in cluster]
            except Exception as error:
                exit(1)

    else:
        logger.error("hostname or clustername required")
    pool.close()
    pool.join()
