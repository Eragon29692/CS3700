#!/usr/bin/python

import sys
import socket
import time
import threading
import string
import getpass
import argparse
import struct
import copy

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

def ether_aton_2(a):
    a = a.replace('-', ':')
    b = map(lambda x: int(x,16), [a[i:i + 2] for i in range(0, len(a), 2)])
    return reduce(lambda x,y: x+y, map(lambda x: struct.pack('B', x), b))
	
def ether_ntoa(n):
    return string.join(map(lambda x: "%02x" % x, 
                           struct.unpack('6B', n)), ':')
						   
def encodeString(n):
	return '\x' + string.join(map(lambda x: "%02x" % x, 
                           struct.unpack('6B', n)), '\x')
                
#convert string to hex:... notation
def to_hex(n):
    return '0x' + "".join(("{:02x}".format(ord(c))) for c in n)
	
class BridgeTableEntry:
    def __init__(self, mac, port, age = 0):
        self.mac = mac
        self.port = port
        self.age = age

class PortInfo:
    def __init__(self, socket, port, logic = 'Designated', forward = 'Listening', timer = 15, vector = eBPDU()):
        self.socket = socket
        self.port = port
        self.logic = logic
        self.forward = forward
        self.timer = timer
                           
class eBPDU:
	def __init__(self, local_port = -1, root_id = None, bridge_id = None, root_pri = None, root_cost = None, bridge_pri = '\x80\x00', port_id = None, msg_age = 0):
		self.root_pri = root_pri
		self.root_id = ether_aton(root_id)
		self.root_cost = root_cost
		self.bridge_pri = self.bridge_pri
		self.bridge_id = ether_aton(self.bridge_id)
		self.port_id = port_id
		self.msg_age = msg_age
		self.local_port = local_port
		
	def decode(packet):
	    self.dst, self.src, self.llc, packetLength, protocol, version, typeP, flags, self.root_pri, self.root_id, self.root_cost, self.bridge_pri, self.bridge_id, self.port_id, self.msg_age = struct.unpack('6s 6s 2s 3s 2s s s s 2s 6s 4s 2s 6s 2s 2s', data[0:32])
		self.msg_age = int(to_hex(self.msg_age))
		self.port_id = int(to_hex(self.port_id))
		self.root_cost = int(to_hex(self.root_cost))
		self.root_pri = encodeString(self.root_pri)
		self.bridge_pri = encodeString(self.bridge_pri)
	def encode():
		return '\x01\x80\xc2\x00\x00\x00' + encodeString(self.bridge_id) + '\x00\x26\x42\x42\x03\x00\x00\x00\x00\x00' + self.root_pri + encodeString(self.root_id) + '\x00\x00\x00' + chr(self.root_cost) + self.bridge_pri + encodeString(self.bridge_id) + '\x00' + chr(self.port_id) + 
                 + chr(self.msg_age) + '\x00\x14\x00\x02\x00\x0f\x00\x00\x00\x00\x00\x00\x00\x00\x00'
						   
def isBetterBPDU(a, b):
	if (a.bridge_pri < b.bridge_pri):
		return True
	if (a.bridge_pri == b.bridge_pri and a.bridge_id < b.bridge_id):
		return True
	if (a.bridge_pri == b.bridge_pri and a.bridge_id == b.bridge_id and a.root_cost < b.root_cost):
		return True
	if (a.bridge_pri == b.bridge_pri and a.bridge_id == b.bridge_id and a.root_cost == b.root_cost and a.port_id < b.port_id):
		return True
	if (a.bridge_pri == b.bridge_pri and a.bridge_id == b.bridge_id and a.root_cost == b.root_cost and a.port_id == b.port_id and a.local_port < b.local_port):
		return True
	return False
	
def receive(s):
    global bridgeTable
    global portInfos
    
    while True:
        dgram = s.recv(1500)
        if not dgram:
            print 'lost connection'
            sys.exit(1)
        dst,src = struct.unpack('6s 6s', dgram[0:12])
        print 'received dgram from %s to %s:' % (ether_ntoa(src), ether_ntoa(dst))
        print string.join(map(lambda x: '%02x' % ord(x), buffer(dgram)[:]), ' ')

        fromPort = getPort(s)
        p = getPortInfo(fromPort)
        if (p.forward == 'Learning' or p.forward == 'Forwarding'):     
            updateOrCreateTableEntry(bridgeTable, src, fromPort)
        
        if (p.forward == 'Forwarding' and ether_ntoa(dst) != '01:80:c2:00:00:00'):
            sendToSocket = getSocketForForwarding(bridgeTable, portInfos, dst, fromPort)
            for x in sendToSocket:
                x.send(dgram)


                
# learning bridge stuff     
    
def timeCounter():
    global currentTime
    global bridgeTable
    while True:
        time.sleep(1)
        currentTime += 1;
        for x in bridgeTable:
            x.age += 1
        bridgeTable[:] = [x for x in bridgeTable if x.age < 15]
		
def portTimer():
    global portInfos
    while True:
        time.sleep(1)
        for x in portInfos:
	    if(x.timer > 0): 
		x.timer -= 1
        
		
def containInTable(table, src):
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


def getSocketForForwarding(bridgeTable, portInfos, dst, fromPort):
    if (containInTable(bridgeTable, dst) == -1):
        return [x.socket for x in portInfos if (fromPort != x.port and x.forward == 'Forwarding')]
    else:
        return [x.socket for x in portInfos if (containInTable(bridgeTable, dst) == x.port and x.forward == 'Forwarding')]

def getPort(socket):
    return socket.getsockname()[-2]
    
def getPortInfo(port):
    global portInfos
    
    for x in portInfos:
        if (port == x.port):
            return x
    return None
    


# main
if __name__ == '__main__':
    mymac = ether_aton(args.mymac[0])
    wirenums = args.wires
    currentTime = 0
    bridgeTable = []
    portInfos =[] 
	root_node = -1

    for wirenum in wirenums:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        s.bind('\0%s.host-%s (wire %d)' % (getpass.getuser(), ether_ntoa(mymac), wirenum))
        if s.connect_ex('\0%s.wire.%d' % (getpass.getuser(), wirenum)):
            print 'connection error'
            sys.exit(1)
        
        
        portInfos.append(PortInfo(s, getPort(s)))
        
        t = threading.Thread(target=receive, args=[s])
        t.daemon = True                   # so ^C works
        t.start()

    timeThread =  threading.Thread(target=timeCounter, args=())
    timeThread.daemon = True
    timeThread.start()    

    timeThread =  threading.Thread(target=portTimer, args=())
    timeThread.daemon = True
    timeThread.start()  


    while True:
        pass
