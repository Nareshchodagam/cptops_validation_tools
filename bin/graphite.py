#!/usr/bin/python
#
import optparse
import os
import sys
import subprocess
from subprocess import PIPE
import socket
import re

def kill_carbon():
	host_check = re.compile(r'mmapp')
	output = host_check.findall(socket.gethostname().split('.')[0])
	if output:
		p1 = subprocess.Popen('ps -ef'.split(), stdout=PIPE)
		p2 = subprocess.Popen('grep carbon-cache'.split(), stdin=p1.stdout, stdout=PIPE)
		p3 = subprocess.Popen('grep ^carbon'.split(), stdin=p2.stdout, stdout=PIPE)
 		p4 = subprocess.Popen('awk {print $2}'.split(' ',1), stdin=p3.stdout, stdout=PIPE)
		proc_list = p4.communicate()[0].rstrip('\n').split('\n')
		for proc_id in proc_list:
			cmd = "kill -9 " + proc_id
			try:
				subprocess.call(cmd.split())
			except subprocess.CalledProcessError:
				error_check(retcode, msg="Error killing carbon-cache process.")
		error_check(0, msg="Carbon-cache killed successfully.")

def httpd_filechk():
	files = ['welcome.conf', 'ssl.conf']
	for file in files:
		if os.path.isfile('/etc/httpd/conf.d/' + file):
			cmd = "rm /etc/httpd/conf.d/" + file
			retcode = subprocess.call(cmd.split())
			error_check(retcode, msg=file + " deleted successfully.")
			if retcode == 0:
				retcode = subprocess.call("service httpd restart".split())
				error_check(retcode, msg="\nRestart HTTPD.")	
		else:
			error_check(0, msg=file + " not present.")
	
def start_metrics():
	host_name = socket.gethostname().split('.')[0]
	metrics_servers = ['ajna-mmcnsmr1-1-sfz', 'ajna-mmcnsmr2-1-sfz']
	if host_name in metrics_servers:
		if os.path.isfile('/opt/ajna-metrics-monitor/bin/runMonitor.sh'):
			cmd = "sudo -u appmon /opt/ajna-metrics-monitor/bin/runMonitor.sh start"
			retcode = subprocess.call(cmd.split())
			error_check(retcode, msg="Metrics monitor started.")

def start_reporter():
	host_name = socket.gethostname().split('.')[0]
	reporter_servers = ['ajna-mmcnsmr6-2-sfz', 'ajna-mmcnsmr8-2-sfz']
	if host_name in reporter_servers:
		if host_name == reporter_servers[0]:
			cmd = "sudo -u appmon /home/appmon/current/ajna-latency-monitor/runReporter.sh start"
			if os.path.isfile('/home/appmon/current/ajna-latency-monitor/pid'):
				subprocess.call('rm /home/appmon/current/ajna-latency-monitor/pid'.split())
			os.chdir('/home/appmon/current/ajna-latency-monitor')
			retcode = subprocess.call(cmd.split())
			error_check(retcode, msg="Latency Reporter started.")
		elif host_name == reporter_servers[1]:
			cmd = "sudo -u appmon /opt/ajnabus-latency-reporter/bin/runReporter.sh start"
			if os.path.isfile('/var/run/ajnabus-latency-reporter/pid'):
				subprocess.call('rm /var/run/ajnabus-latency-reporter/pid'.split())
			os.chdir('/opt/ajnabus-latency-reporter/bin')
			retcode = subprocess.call(cmd.split())
			error_check(retcode, msg="Latency Reporter started.")

def error_check(retcode, msg):
    if retcode != 0:
        print msg + " = Failed\n"
        sys.exit(1)
    else:
        print msg + " = OK\n"
        
if __name__ == "__main__":
    usage="""
 			To kill carbon-cache processes on Storage node. 
 			python graphite.py --kill-carbon
 			
 			To start metrics monitor. 
 			python graphite.py --start-metrics
 			
 			To start Latency reporter. 
 			python graphite.py --start-reporter
 			
 			To reconfigure HTTPD services.
 			python graphite.py --http-check
 			
          """
    parser = optparse.OptionParser(usage)
    parser.add_option("--kill-carbon", action='store_true', dest='cache', help="Kill carbon-cache processes")
    parser.add_option("--start-metrics", action='store_true', dest="metrics", help="Start Metrics monitor")
    parser.add_option("--start-reporter", action='store_true', dest="reporter", help="Start Latency reporter")
    parser.add_option("--http-check", action='store_true', dest='httpchk', help="Check HTTP configuration")
    (options, args) = parser.parse_args()
    
    if options.cache:
    	kill_carbon()
    
    if options.metrics:
    	start_metrics()
    	
    if options.reporter:
    	start_reporter()
    
    if options.httpchk:
    	httpd_filechk()
    
    if not options.cache and not options.metrics and not options.reporter and not options.httpchk:
    	print(usage)
