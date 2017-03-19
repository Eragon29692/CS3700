#!/usr/bin/python
import sys
import socket
import string
import binascii
import struct 
import random
import time

# hex string addition. Convert hex byte string to hex number string. Exp: '\x12\x34' -> '0x1234'
# then convert to int number, add it with integer add. Then return the new hex byte string
def hex_addition(n, add):
    return format(int('0x' + "".join(("{:02x}".format(ord(c))) for c in n), 0) + add, '0' + str(len(n) * 2) + 'x').decode('hex')

def send(pkt):
    global s
    global fp
    hdr = struct.pack('!H', len(pkt))
    s.send(hdr + pkt)
    phdr = struct.pack("IIII", 0, 0, len(pkt), len(pkt))
    fp.write(phdr + pkt)

def recv():
    global s
    global fp
    hdr = s.recv(2)
    pktlen = struct.unpack('!H', hdr)[0]
    pkt = s.recv(pktlen)
    phdr = struct.pack("IIII", 0, 0, len(pkt), len(pkt))
    fp.write(phdr + pkt)
    return pkt

def ip_cksum(pkt):
    if len(pkt) & 1:
        pkt += '\0'
    sum = 0
    for i in range(0, len(pkt)-1, 2):
        sum += struct.unpack_from("!H", pkt, offset=i)[0]
    while (sum > 0xffff):
        sum = (sum & 0xffff) + (sum >> 16)
    return sum ^ 0xffff

class Packet:
    def __init__(self, packetId = '\x00\x00', ipchecksum = '\x04\xec', seqNum = '\x00\x00\x00\x00', ackNum = '\x00\x00\x00\x00', tcpchecksum = '\xee\xfa', data = ''):
        self.packetId = packetId
        self.ipchecksum = ipchecksum
        self.seqNum = seqNum
        self.ackNum = ackNum
        #self.flag = flag
        self.tcpchecksum = tcpchecksum
        self.data = data
        self.portRand = format(random.randint(4096, 65535), '04x').decode('hex')

    #update this package with the received packet
    def decode(self, packet):
        #ackSeq is the received seqNum
        self.ackNum = packet[38:42]

    def buildIpChecksum(self, data = ''):
        return format(ip_cksum('\x45\x00' + hex_addition('\x00\x28', len(data)) + self.packetId + '\x00\x00\x40\x06\x0a\xAF\x61\x34\x0a\x00\x00\x01'), '04x').decode('hex')

    def buildTCPChecksum(self, port = '', seqNum = '', ackNum = '',flag = '', data = ''):
        return format(ip_cksum('\x0a\xAF\x61\x34\x0a\x00\x00\x01\x00\x06' + hex_addition('\x00\x14', len(data)) + port + '\x00\x50' +seqNum + ackNum + '\x50' + flag + '\x05\x78\x00\x00' + data), '04x').decode('hex')

    def buildPacket(self, seqAdd = 0, ackAdd = 0, flag = '\x02', data = ''):
        self.packetId = hex_addition(self.packetId, 1)
        self.seqNum = hex_addition(self.seqNum, seqAdd)
        self.ackNum = hex_addition(self.ackNum, ackAdd)
        return '\x02\x00\x00\x00\x00\x01\x02\x00\x01\x75\x97\x52\x08\x00\x45\x00' + hex_addition('\x00\x28', len(data)) + self.packetId + '\x00\x00\x40\x06' + self.buildIpChecksum(data) + '\x0a\xAF\x61\x34\x0a\x00\x00\x01' + self.portRand + '\x00\x50' + self.seqNum + self.ackNum + '\x50' + flag + '\x05\x78' + self.buildTCPChecksum(self.portRand, self.seqNum, self.ackNum, flag, data) + '\x00\x00' + data

# main
if __name__ == '__main__':
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    s.connect(('login-faculty.ccs.neu.edu', 5025))
    fp = open("log.pcap", "w")
    fhdr = struct.pack("IHHIIII", 0xa1b2c3d4, 2, 4, 0, 0, 65536, 1);
    fp.write(fhdr)
    myPacket = Packet()

    INITIAL_ARP = (
        '\xFF\xFF\xFF\xFF\xFF\xFF' #dst ethr
        '\x02\x00\x01\x75\x97\x52' #src ethr
        '\x08\x06' #ethrtype = ARP
        '\x00\x01\x08\x00' #hwtype = ethrnet, prottype = IP
        '\x06\x04' #hwadrr len = 6, protlen = 4
        '\x00\x01' #optype = request
        '\x02\x00\x01\x75\x97\x52' #sender ether addr
        '\x0a\xAF\x61\x34' #sender ip
        '\x00\x00\x00\x00\x00\x00' #target ether
        '\x0a\x00\x00\x01' #target ip
    )
    

    #(1) -------- ARP REQ ------->
    #<-------- ARP REPLY -------
    send(INITIAL_ARP)
    tmp = recv()
    print binascii.hexlify(tmp)


    #(2) --------- SYN ----------> (a)
    #<-------- SYN|ACK --------- (b)
    #----------- ACK ----------> (c)
    send(myPacket.buildPacket())
    tmp = recv()
    print binascii.hexlify(tmp)
    myPacket.decode(tmp)
    send(myPacket.buildPacket(1, 1, '\x10'))

    #(3) -- "GET / HTTP/1.0\n\n"->
    #<----------- ACK ---------- 
    getData = '\x47\x45\x54\x20\x2f\x20\x48\x54\x54\x50\x2f\x31\x2e\x30\x0d\x0a\x0d\x0a'
    send(myPacket.buildPacket(0, 0,'\x10', getData))
    tmp = recv()
    myPacket.decode(tmp)
    print binascii.hexlify(tmp)
    
    #(4)<-- HTTP/1.1 200 OK... ---
    #----------- ACK ---------->
    tmp = recv()
    myPacket.decode(tmp)
    dataReceived = tmp[54:]
    print binascii.hexlify(tmp)
    
    #(5) <---- FIN | ACK ---------(a)
    #--------FIN | ACK -------->(b)
    tmp = recv()
    myPacket.decode(tmp)
    print binascii.hexlify(tmp)
    send(myPacket.buildPacket(18, len(dataReceived),'\x11'))
    


