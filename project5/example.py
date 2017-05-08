#!/usr/bin/python
#
# simple program to connect to message bus and send messages
#

import sys
import socket
import time
import threading
import string
import getpass
import argparse

parser = argparse.ArgumentParser(description='example - send messages on message bus')
parser.add_argument('nodeid', metavar='n', type=int, nargs=1,
                    help='Node ID')
args = parser.parse_args()
nodeid = args.nodeid[0]

def receive(s):
    while True:
        dgram = s.recv(4096)
        if not dgram:
            print 'lost connection'
            sys.exit(1)
        print 'received:'
        for line in dgram.split('\n'):
            print ' ', line

if __name__ == '__main__':
    s = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    s.bind('\0%s.test-%d' % (getpass.getuser(), nodeid))
    if s.connect_ex('\0%s.bus.%d' % (getpass.getuser(), nodeid)):
        print 'connection error'
        sys.exit(1)

    t = threading.Thread(target=receive, args=[s])
    t.daemon = True                   # so ^C works
    t.start()

    seq = 0
    while True:
        for i in range(9):
            time.sleep(1)
            pkt = "To: %d\nFrom: %d\nCmd: test\nId: %d\nKey: \nValue: \n" % (i, nodeid, seq)
            s.send(pkt)
            seq += 1
