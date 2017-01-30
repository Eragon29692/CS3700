#!/bin/python
import sys
import socket
import time
import threading
import string
import getpass
import argparse
import struct


def ether_aton(a):
    a = a.replace('-', ':')
    b = map(lambda x: int(x,16), a.split(':'))
    return reduce(lambda x,y: x+y, map(lambda x: struct.pack('B', x), b))

def ether_ntoa(n):
    return string.join(map(lambda x: "%02x" % x, 
                           struct.unpack('6B', n)), ':')
def print_hex(n):
    return ":".join("{:02x}".format(ord(c)) for c in n)


class ether:
    def __init__(self):
        self.dst = dst
        self.src = src
        self.data = data
    def decode(self, packet):
        self.src, self.dst = struct.unpack('6s 6s', packet[0:12])
        data = packet[13:]
    def print_ether(self):
        print 'ether_src: %s' %(ether_ntoa(self.src))
        print 'ether_dst: %s' %(ether_ntoa(self.dst))


class bpdu:
    def __init__(self)


if sys.argv[1] == 'decode':
    buff = sys.stdin.read()
    print buff
    #fields = struct.unpack('!6s6sH3BH BBBQIQHHHHH', sys.stdin.read())
    #a,b,c,d,e,f,g,h,i =  struct.unpack('6s 6s 2s 3s 2s s s s 8s', buff[0:30])
    etherPacket = E

if sys.argv[1] == 'encode':
    print 'encode'
