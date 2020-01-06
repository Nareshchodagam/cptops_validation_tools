#!/bin/bash

SERVICES='mongodb elasticsearch graylog http-graylog-health gelf-health gelf-storm-log-health tcp-syslog-health'
SYSTEMD_PATH="/etc/systemd/system"

VALIDATED="TRUE"

for service in ${SERVICES}
do
    if [ -f "${SYSTEMD_PATH}/${service}.service" ]; then
        echo "*** checking that ${service} is running"
        service ${service} status
        if [ "$?" != 0 ]; then
            echo -e '\tSERVICE ${service} is not running'
            VALIDATED="FALSE"
        fi
    fi
done

# Make sure that all our services are actually running; no sense in going
# further if they're not.
if [ "${VALIDATED}" == "TRUE" ]; then
    echo "*** all netlog services on `hostname` are running"
else
    echo "*** some netlog services on `hostname` are not running, service validation failed!"
    exit 1
fi

# Check that the elasticsearch cluster is back online and healthy
ELASTIC_HOST=`hostname`
ELASTIC_STATUS=`curl -s -XGET http://${ELASTIC_HOST}:9200/_cluster/health?pretty=true | grep status | awk '{ print $3 }' | sed -e 's/"//g' | sed -e 's/,//g'`
if [ "${ELASTIC_STATUS}" = "green" ]; then
    echo "*** Elasticsearch cluster status on ${ELASTIC_HOST} is green"
else
    echo "*** Elasticsearch cluster status on ${ELASTIC_HOST} is not healthy: ${ELASTIC_STATUS}"
    exit 1
fi

exit 0
