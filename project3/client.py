#!/usr/bin/python
import sys
import socket
import string
import binascii
import struct 
import random

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
    return s.recv(pktlen)

def ip_cksum(pkt):
    if len(pkt) & 1:
        pkt += '\0'
    sum = 0
    for i in range(0, len(pkt)-1, 2):
        sum += struct.unpack_from("!H", pkt, offset=i)[0]
    while (sum > 0xffff):
        sum = (sum & 0xffff) + (sum >> 16)
    return sum ^ 0xffff


# main
if __name__ == '__main__':
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    s.connect(('login-faculty.ccs.neu.edu', 5025))
    fp = open("log.pcap", "w")
    fhdr = struct.pack("IHHIIII", 0xa1b2c3d4, 2, 4, 0, 0, 65536, 1);
    fp.write(fhdr)
 
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
    
    send(INITIAL_ARP)
    tmp = recv()
    print binascii.hexlify(tmp)

    portRand = format(random.randint(10, 99), '02x').decode('hex')
    print portRand      
    INITIAL_SYN1 = (
        '\xFF\xFF\xFF\xFF\xFF\xFF' #dst ethr
        '\x02\x00\x01\x75\x97\x52' #src ethr
        '\x08\x00\x45\x00' #type
        '\x00\x28' #len
        '\x00\x01' #ID
        '\x00\x00\x40\x06'
        '\x04\xec' #checksum
        '\x0a\xAF\x61\x34'
        '\x0a\x00\x00\x01'
    ) 
    INITIAL_SYN2 = (
        #random src port
        '\x00\x50' #port 80
        '\x0a\x00\x00\x01'
        '\x00\x00\x00\x00'
        '\x50' #offest = 5
        '\x02' #SYN
        '\x05\x78' #window
        '\xee\xfa\x00\x00'
    )

    #print ip_cksum(INITIAL_SYN)
    
    INITIAL_SYN = (
        '\xFF\xFF\xFF\xFF\xFF\xFF' #dst ethr
        '\x02\x00\x01\x75\x97\x52' #src ethr
        '\x08\x00\x45\x00' #type
        '\x00\x36' #len
        '\x00\x01' #ID
        '\x00\x00\x40\x06'
        '\xce\xf9' #checksum
        '\x0a\xAF\x61\x34'
        '\x0a\x00\x00\x01'
        '\x30\x31'#random src port
        '\x00\x50' #port 80
        '\x0a\x00\x00\x01'
        '\x00\x00\x00\x00'
        '\x50' #offest = 5
        '\x02' #SYN
        '\x05\x78' #window
        '\xee\xfa' #checksum
        '\x00\x00'
    )

    f = open("hexdump","w") #opens file with name of "test.txt"
    f.write(INITIAL_SYN1 + portRand + portRand + INITIAL_SYN2)
    f.close()
    send(INITIAL_SYN1 + portRand + portRand + INITIAL_SYN2)
    #send(INITIAL_SYN)
    tmp = recv()
    print binascii.hexlify(tmp)


