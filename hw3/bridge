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
    return string.join(chr(map(lambda x: "%02x" % x, 
                           struct.unpack('6B', n))), '')
                
#convert string to hex:... notation
def to_hex(n):
    return '0x' + "".join(("{:02x}".format(ord(c))) for c in n)
    
class BridgeTableEntry:
    def __init__(self, mac, port, age = 0):
        self.mac = mac
        self.port = port
        self.age = age


# class to decode BPDU                           
class eBPDU:
    def __init__(self, local_port = -1, root_id = '00:00:00:00:00:00', bridge_id = '00:00:00:00:00:00', port_id = None, root_cost = 0, root_pri = '\x80\x00', bridge_pri = '\x80\x00', msg_age = 0):
        self.root_pri = root_pri
        self.root_id = ether_aton(root_id)
        self.root_cost = root_cost
        self.bridge_pri = bridge_pri
        self.bridge_id = ether_aton(bridge_id)
        self.port_id = port_id
        self.msg_age = msg_age
        self.local_port = local_port
    
    # decoding a package
    def decode(self, packet):
        self.dst, self.src, self.llc, packetLength, protocol, version, typeP, flags, self.root_pri, self.root_id, self.root_cost, self.bridge_pri, self.bridge_id, self.port_id, self.msg_age = struct.unpack('6s 6s 2s 3s 2s s s s 2s 6s 4s 2s 6s 2s 2s', packet[0:46])
        self.msg_age = int(to_hex(self.msg_age), 0)
        self.port_id = int(to_hex(self.port_id), 0)
        self.root_cost = int(to_hex(self.root_cost), 0)
    
    #encoding a package    
    def encode(self):
        return '\x01\x80\xc2\x00\x00\x00' + self.bridge_id + '\x00\x26\x42\x42\x03\x00\x00\x00\x00\x00' + self.root_pri + self.root_id + format(self.root_cost, '08x').decode('hex') + self.bridge_pri + self.bridge_id + format(self.port_id, '04x').decode('hex') + format(self.msg_age, '04x').decode('hex') + '\x14\x00\x02\x00\x0f\x00\x00\x00\x00\x00\x00\x00\x00\x00'


# stores information of each port
class PortInfo:
    def __init__(self, socket, port, vector, logic = 'Designated', forward = 'Listening', timer = 15):
        self.socket = socket
        self.port = port
        self.logic = logic
        self.forward = forward
        self.timer = timer
        self.vector = vector

#if BPDU a is better than b returns T/F 
def isBetterBPDU(a, b, cost_reduce = 0):
    if (a.bridge_pri < b.bridge_pri):
        return True
    if (a.bridge_pri == b.bridge_pri and a.bridge_id < b.bridge_id):
        return True
    if (a.bridge_pri == b.bridge_pri and a.bridge_id == b.bridge_id and a.root_cost - cost_reduce < b.root_cost):
        return True
    if (a.bridge_pri == b.bridge_pri and a.bridge_id == b.bridge_id and a.root_cost == b.root_cost and a.port_id < b.port_id):
        return True
    if (a.bridge_pri == b.bridge_pri and a.bridge_id == b.bridge_id and a.root_cost == b.root_cost and a.port_id == b.port_id and a.local_port < b.local_port):
        return True
    return False

#if BPDU a is equal as b returns T/F
def isEqualBPDU(a, b):
    if not isBetterBPDU(a, b) and not isBetterBPDU(b, a):
        return True
    else:
        return False

#what to do when a BPDU arrives
def receive(s):
    global bridgeTable
    global portInfos
    global bridge_bpdu
    global root_port

    while True:
        dgram = s.recv(1500)
        if not dgram:
            print 'lost connection'
            sys.exit(1)
        dst, src = struct.unpack('6s 6s', dgram[0:12])
        print 'received dgram from %s to %s:' % (ether_ntoa(src), ether_ntoa(dst))
        print string.join(map(lambda x: '%02x' % ord(x), buffer(dgram)[:]), ' ')

        fromPort = getPort(s)
        p = getPortInfo(fromPort)
        if p.forward == 'Learning' or p.forward == 'Forwarding':
            updateOrCreateTableEntry(bridgeTable, src, fromPort)

        if p.forward == 'Forwarding' and ether_ntoa(dst) != '01:80:c2:00:00:00':
            sendToSocket = getSocketForForwarding(bridgeTable, portInfos, dst, fromPort)
            for x in sendToSocket:
                x.send(dgram)

        if ether_ntoa(dst) == '01:80:c2:00:00:00':
            
            receivedBPDU = eBPDU()
            receivedBPDU.decode(dgram)
            
                
            p.vector = copy.deepcopy(receivedBPDU)
            p.vector.msg_age += 256
            #p.vector.root_cost += 10
            p.vector.local_port = fromPort
            if isEqualBPDU(p.vector, bridge_bpdu):
                bridge_bpdu.msg_age = p.vector.msg_age
            #spanning tree operations
            if isBetterBPDU(p.vector, bridge_bpdu):
                flag = True
            for x in portInfos:
                if isBetterBPDU(p.vector, bridge_bpdu):
                    if (flag):
                        bridge_bpdu.root_cost = x.vector.root_cost + 10
                        flag = False
                    bridge_bpdu.msg_age = x.vector.msg_age
                    bridge_bpdu.local_port = x.vector.local_port
                    bridge_bpdu.root_id = x.vector.root_id
                    root_port = x.port
            
            for x in portInfos:
                if x.port == root_port:
                    if x.logic != 'Root':
                        x.logic = 'Root'
                        x.forward = 'Listening'
                        x.timer = 15
                if x.port != root_port:
                    tmp = copy.deepcopy(bridge_bpdu)

                    if isBetterBPDU(bridge_bpdu, x.vector):
                        if x.logic != 'Designated':
                            x.logic = 'Designated'
                            x.forward = 'Listening'
                            x.timer = 15
                    if isBetterBPDU(x.vector, bridge_bpdu):
                        if x.logic != 'Blocked':
                            x.logic = 'Blocked'
                            x.forward = 'Blocked'
                            x.timer = 0
                #print 'port {} is forward: {}, cost {}'.format(x.port, x.forward, x.vector.root_cost)



# removing timeout entry from the learning brdig etable 
def timeCounter():
    global currentTime
    global bridgeTable
    while True:
        time.sleep(1)
        currentTime += 1
        for x in bridgeTable:
            x.age += 1
        bridgeTable[:] = [x for x in bridgeTable if x.age < 15]

#timeout for the port every one second
def portTimer():
    global portInfos
    while True:
        time.sleep(1)
        for x in portInfos:
            if (x.timer > 0): 
                x.timer -= 1
                if (x.timer == 0):
                    if (x.forward == 'Learning'):
                        x.forward = 'Forwarding'
                    if (x.forward == 'Listening'):
                        x.timer = 15
                        x.forward = 'Learning'
#sending BPDU every 2 seconds
def sendBPDU():
    global portInfos
    global bridge_bpdu
    
    while True:
        time.sleep(2)
        for x in portInfos:
            tmp = copy.deepcopy(bridge_bpdu)
            tmp.port_id = int(x.port)
            tmp.bridge_id = mymac
            x.socket.send(tmp.encode())

#creating the BPDU timeout
def eBPDUTimeout():
    global portInfos
    global no_bridge
    global bridge_bpdu
    global root_port
    while True:
        time.sleep(1)
        for x in portInfos:
            if(x.vector.msg_age > 0):
                x.vector.msg_age += 256
            if(x.vector.msg_age > 20 * 256):
                x.vector = copy.deepcopy(no_bridge)
        if(bridge_bpdu.msg_age > 0):
            bridge_bpdu.msg_age += 256
            if(bridge_bpdu.msg_age > 20 * 256):
                bridge_bpdu = copy.deepcopy(my_bpdu)
                root_port = -1
        
            
#is the src in the learning bridge table        
def containInTable(table, src):
    for x in table:
        if (x.mac == src):
            return x.port
    return -1

#update or create entry in the learning brdige table
def updateOrCreateTableEntry(bridgeTable, src, fromPort, age = 0):
    if (containInTable(bridgeTable, src) != -1):
        for x in bridgeTable:
            if (x.mac == src):
                x.port = fromPort
                x.age = age
    else:
        bridgeTable.append(BridgeTableEntry(src, fromPort))

#gets the socket to forward too
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
    root_port = -1
    my_bpdu = eBPDU(-1, ether_ntoa(mymac), ether_ntoa(mymac))
    no_bridge = eBPDU(-1, ether_ntoa(mymac), ether_ntoa(mymac), None, 0, '\xff\xff')

    bridge_bpdu = copy.deepcopy(my_bpdu)

    for wirenum in wirenums:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        s.bind('\0%s.host-%s (wire %d)' % (getpass.getuser(), ether_ntoa(mymac), wirenum))
        if s.connect_ex('\0%s.wire.%d' % (getpass.getuser(), wirenum)):
            print 'connection error'
            sys.exit(1)
        
        
        portInfos.append(PortInfo(s, getPort(s), copy.deepcopy(no_bridge)))
        
        t = threading.Thread(target=receive, args=[s])
        t.daemon = True                   # so ^C works
        t.start()

    timeThread =  threading.Thread(target=timeCounter, args=())
    timeThread.daemon = True
    timeThread.start()    

    timeThread =  threading.Thread(target=portTimer, args=())
    timeThread.daemon = True
    timeThread.start()  

    timeThread =  threading.Thread(target=sendBPDU, args=())
    timeThread.daemon = True
    timeThread.start()

    timeThread =  threading.Thread(target=eBPDUTimeout, args=())
    timeThread.daemon = True
    timeThread.start()

    while True:
        pass
