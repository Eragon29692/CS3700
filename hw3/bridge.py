#!/usr/bin/python

import sys
import socket
import time
import threading
import string
import getpass
import argparse
import struct


parser = argparse.ArgumentParser(description='Bridge - send packets across the "network"')
parser.add_argument('mymac', metavar='ll:ll:ll:ll:ll:ll', type=str, nargs=1,
                    help='local MAC address')
parser.add_argument('wires', metavar='W', type=int, nargs='+',
                    help='wire # to connect to')
                   
args = parser.parse_args() 
                    
def ether_aton(a):
    a = a.replace('-', ':')
    b = map(lambda x: int(x,16), a.split(':'))
    return reduce(lambda x,y: x+y, map(lambda x: struct.pack('B', x), b))

def ether_ntoa(n):
    return string.join(map(lambda x: "%02x" % x, 
                           struct.unpack('6B', n)), ':')
                
class BridgeTableEntry:
    def __init__(self, mac, port, age = 0):
        self.mac = mac
        self.port = port
        self.age = age


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
    
    def encode(self):
        #the last 4 zero is to default the length
        return self.dst.replace(':', '') + self.src.replace(':', '') + '0026'
    
    #print out the src and dst
    def print_packet(self):
        print 'ether_src: %s' %(ether_ntoa(self.src))
        print 'ether_dst: %s' %(ether_ntoa(self.dst))
 
           
                           
def receive(s):
    global bridgeTable
    global sockets
    
    while True:
        dgram = s.recv(1500)
        if not dgram:
            print 'lost connection'
            sys.exit(1)
        dst,src = struct.unpack('6s 6s', dgram[0:12])
        print 'received dgram from %s to %s:' % (ether_ntoa(src), ether_ntoa(dst))
        print string.join(map(lambda x: '%02x' % ord(x), buffer(dgram)[:]), ' ')
        #print 'port: {}'.format(s.getsockname()[-2])
        fromPort = getPort(s)
    
        updateOrCreateTableEntry(bridgeTable, src, fromPort)
        
        if (ether_ntoa(dst) != '01:80:c2:00:00:00'):
            sendToSocket = getSocketForForwarding(bridgeTable, sockets, dst, fromPort)
            for x in sendToSocket:
                x.send(dgram)

        
def timeCounter():
    global currentTime
    global bridgeTable
    while True:
        time.sleep(1)
        currentTime += 1;
        for x in bridgeTable:
            x.age += 1
        bridgeTable[:] = [x for x in bridgeTable if x.age < 15]

def containInTable(table, src):
    #return len([x for x in table if x.mac == src]) != 0
    for x in table:
        if (x.mac == src):
            return x.port
    return -1

def updateOrCreateTableEntry(bridgeTable, src, fromPort, age = 0):
    if (containInTable(bridgeTable, src) != -1):
        for x in bridgeTable:
            if (x.mac == src):
                x.port = fromPort
                x.age = age
    else:
        bridgeTable.append(BridgeTableEntry(src, fromPort))


def getSocketForForwarding(bridgeTable, sockets, dst, fromPort):
    if (containInTable(bridgeTable, dst) == -1):
        return [x for x in sockets if fromPort != getPort(x)]
    else:
        return [x for x in sockets if containInTable(bridgeTable, dst) == getPort(x)]

def getPort(socket):
    return socket.getsockname()[-2]

def test():
    #global currentTime
    while True:
        print 'time: %d' %(currentTime)
        time.sleep(1)


if __name__ == '__main__':
    mymac = ether_aton(args.mymac[0])
    wirenums = args.wires
    currentTime = 0
    bridgeTable = []
    sockets = []

    for wirenum in wirenums:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        s.bind('\0%s.host-%s (wire %d)' % (getpass.getuser(), ether_ntoa(mymac), wirenum))
        if s.connect_ex('\0%s.wire.%d' % (getpass.getuser(), wirenum)):
            print 'connection error'
            sys.exit(1)
        
        sockets.append(s)

        t = threading.Thread(target=receive, args=[s])
        t.daemon = True                   # so ^C works
        t.start()

    timeThread =  threading.Thread(target=timeCounter, args=())
    timeThread.daemon = True
    timeThread.start()    
    
   # testThread =  threading.Thread(target=test, args=())
   # testThread.daemon = True
   # testThread.start()


    while True:
        pass
        
