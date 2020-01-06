import socket
from argparse import ArgumentParser

parser = ArgumentParser(prog="rack_port_check.py", usage="%(prog)s --host host_ip --port port")
parser.add_argument("--host", dest="ip", help="rackip", required=True)
parser.add_argument("--port", dest="port", help="port", default=22)

args = parser.parse_args()

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
result = sock.connect_ex((args.ip, args.port))
sock.close()

if result == 0:
    print("open")
else:
    print("closed")
