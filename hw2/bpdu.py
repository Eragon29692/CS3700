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

#convert string to hex:... notation
def to_hex(n):
    return '0x' + "".join(("{:02x}".format(ord(c))) for c in n)


#ethernet packet
class Ether:
    #initialize class
    def __init__(self, dst = None, src = None, data = None):
        self.dst = dst
        self.src = src
        self.data = data

    #decode the packet to get src and dst
    def decode(self, packet):
        #get the 2 first 6 bytes addresses
        self.dst, self.src = struct.unpack('6s 6s', packet[0:12])
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
    #make sure decode from 0 to 32 with the 3 timer values add up to a total of 38 bytes
    def decode(self, data):
        self.llc, self.protocol, self.version, self.type, self.flags, self.stp_root_pri, self.stp_root_mac, self.stp_root_cost, self.stp_bridge_pri, self.stp_bridge_mac, self.stp_port_id, self.stp_msg_age = struct.unpack('3s 2s s s s 2s 6s 4s 2s 6s 2s 2s', data[0:32])

    #print out the src and dst
    def print_packet(self):
        print 'type: {} # ({})'.format(int(to_hex(self.type), 0), to_hex(self.type))
        print 'flags: {} # ({})'.format(int(to_hex(self.flags), 0), to_hex(self.flags))
        print 'stp_root_pri: {} # ({})'.format(int(to_hex(self.stp_root_pri), 0), to_hex(self.stp_root_pri))
        print 'stp_root_cost: {} # ({})'.format(int(to_hex(self.stp_root_cost), 0), to_hex(self.stp_root_cost))
        print 'stp_bridge_pri: {} # ({})'.format(int(to_hex(self.stp_bridge_pri), 0), to_hex(self.stp_bridge_pri))
        print 'stp_port_id: {} # ({})'.format(int(to_hex(self.stp_port_id), 0), to_hex(self.stp_port_id))
        print 'stp_msg_age: {} # ({})'.format(int(to_hex(self.stp_msg_age), 0), to_hex(self.stp_msg_age))
        print 'stp_root_mac: {}'.format(ether_ntoa(self.stp_root_mac))
        print 'stp_bridge_mac: {}'.format(ether_ntoa(self.stp_bridge_mac)) 


if sys.argv[1] == 'decode':
    buff = sys.stdin.read()
    #new empty ethernet packet
    etherPacket = Ether()
    etherPacket.decode(buff)
    etherPacket.print_packet()
    
    #check for destination address
    if (ether_ntoa(etherPacket.dst) == '01:80:c2:00:00:00'):
        #check for the LLC bits
        #if (to_hex(struct.unpack('3s', etherPacket.data[0:3])[0]) == '0x424203'):
        bpduPacket = BPDU()
        bpduPacket.decode(etherPacket.data)
        if (to_hex(bpduPacket.llc) == '0x424203' and to_hex(bpduPacket.protocol) == '0x0000' and to_hex(bpduPacket.version) == '0x00' and to_hex(bpduPacket.flags) == '0x00' and to_hex(bpduPacket.type) == '0x00'):    
            bpduPacket.print_packet()
    
  

if sys.argv[1] == 'encode':
    print 'encode'
