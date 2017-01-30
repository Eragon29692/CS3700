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


#ethernet packet
class Ether:
    #initialize class
    def __init__(self):
        self.dst = None
        self.src = None
        self.data = None

    #decode the packet to get src and dst
    def decode(self, packet):
        #get the 2 first 6 bytes addresses
        self.src, self.dst = struct.unpack('6s 6s', packet[0:12])
        #data starting from the 15th bytes after the 12 bytes addresses and 2 bytes of length
        self.data = packet[14:]

    #print out the src and dst
    def print_packet(self):
        print 'ether_src: %s' %(ether_ntoa(self.src))
        print 'ether_dst: %s' %(ether_ntoa(self.dst))



#Spanning tree packet 
#which will be decoded from the data field of the ethernet packet
class BPDU:
    #initialize class
    def __init__(self):
        self.llc = None
        self.protocol = None
        self.version = None
        self.type = None
        self.flags = None
        self.stp_root_pri = None
        self.stp_root_cost = None
        self.stp_bridge_pri = None
        self.stp_port_id = None
        self.stp_msg_age = None
        self.stp_root_mac = None
        self.stp_bridge_mac = None
        self.max_age = 20
        self.hello_time = 2
        self.forward_delay = 15

    #decode the data
    def decode(self, data):
        self.llc, self.protocol, self.version, self.type, self.flags, self.stp_root_pri, self.stp_root_mac, self.stp_root_cost, self.stp_bridge_pri, self.stp_bridge_mac, self.stp_port_id, self.stp_msg_age = struct.unpack('3s 2s B B B 2s 6s 4s 2s 6s 2s 2s', data[0:32])

    #print out the src and dst
    def print_packet(self):
        print 'type: %s' %(self.type)
        print 'flags: %s' %(self.flags)
        print 'stp_root_pri: %s' %(print_hex(self.stp_root_pri))


        print 'stp_root_mac: %s' %(ether_ntoa(self.stp_root_mac)) 


if sys.argv[1] == 'decode':
    buff = sys.stdin.read()
    #new empty ethernet packet
    etherPacket = Ether()
    etherPacket.decode(buff)
    etherPacket.print_packet()

    print print_hex(etherPacket.data)

    bpduPacket = BPDU()
    bpduPacket.decode(etherPacket.data)
    bpduPacket.print_packet()
  

if sys.argv[1] == 'encode':
    print 'encode'
