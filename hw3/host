#!/usr/bin/python
#
# simple program to connect to a "wire" and send ethernet packets between two hosts
#

import sys
import socket
import time
import threading
import string
import getpass
import argparse
import struct

# usage: host <mac> <wire> <remote-mac>

parser = argparse.ArgumentParser(description='Host - send packets across the "network"')
parser.add_argument('mymac', metavar='ll:ll:ll:ll:ll:ll', type=str, nargs=1,
                    help='local MAC address')
parser.add_argument('wire', metavar='W', type=int, nargs=1,
                    help='wire # to connect to')
parser.add_argument('remote', metavar='rr:rr:rr:rr:rr:rr', type=str, nargs=1,
                    help='destination MAC address')
parser.add_argument('--silent', action='store_true', help='receive only, no transmit')
args = parser.parse_args()

def ether_aton(a):
    a = a.replace('-', ':')
    b = map(lambda x: int(x,16), a.split(':'))
    return reduce(lambda x,y: x+y, map(lambda x: struct.pack('B', x), b))

def ether_ntoa(n):
    return string.join(map(lambda x: "%02x" % x, 
                           struct.unpack('6B', n)), ':')

def receive(s):
    while True:
        dgram = s.recv(1500)
        if not dgram:
            print 'lost connection'
            sys.exit(1)
        dst,src = struct.unpack('6s 6s', dgram[0:12])
        print 'received dgram from %s to %s:' % (ether_ntoa(src), ether_ntoa(dst))
        print string.join(map(lambda x: '%02x' % ord(x), buffer(dgram)[:]), ' ')
        print ''

if __name__ == '__main__':
    mymac = ether_aton(args.mymac[0])
    wirenum = args.wire[0]
    remote = ether_aton(args.remote[0])

    s = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    s.bind('\0%s.host-%s (wire %d)' % (getpass.getuser(), ether_ntoa(mymac), wirenum))
    if s.connect_ex('\0%s.wire.%d' % (getpass.getuser(), wirenum)):
        print 'connection error'
        sys.exit(1)


    t = threading.Thread(target=receive, args=[s])
    t.daemon = True                   # so ^C works
    t.start()

    pkt_data = string.join(map(chr, (0xDE,0xAD,0xBE,0xEF,0xDE,0xAD,0xBE,0xEF)), '')
    bogus_ethertype = 0x900
    pkt = struct.pack('!6s 6s H', remote, mymac, bogus_ethertype) + pkt_data
    if len(pkt) < 60:
        pkt = pkt + '\0' * (60-len(pkt))
        
    while True:
        time.sleep(3)
        if not args.silent:
            s.send(pkt)
