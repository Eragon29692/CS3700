#!/usr/bin/python
#
# test-lb.py - test learning bridge functionality
#

import random, threading, subprocess
import select, time, string
import struct, socket
import signal, sys, getpass
import argparse

#------------------------------------

# test infrastructure. 'wires' and 'bridge' will run in separate processes,
# and this process will connect sockets to 'wires' and transmit/receive
# packets

listeners = []

# connect to a wire and return a socket
def connect(wirenum, local):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    s.bind('\0%s.host-%s)' % (getpass.getuser(), local))
    if s.connect_ex('\0%s.wire.%d' % (getpass.getuser(), wirenum)):
        print 'connection error'
        sys.exit(1)
    return s

# socket listener - save received datagrams
class listener:
    def __init__(self, sock, responder=None):
        self.sock,self.responder = sock,responder
        listeners.append(self)
        self.received = []
        self.error = None
    def done(self):
        listeners.remove(self)
    def pkts(self):
        tmp = self.received
        self.received = []
        return tmp

def find_listener(sock):
    for l in listeners:
        if l.sock == sock:
            return l
    return None

def hexdump(pkt):
    return ' '.join(['%02x' % ord(x) for x in pkt[:]])

# listen on all sockets
def _listen_thread():
    while True:
        rfds,ign1,ign2 = select.select([x.sock for x in listeners], [], [])
        for s in rfds:
            dgram = s.recv(1500)
            l = find_listener(s)
            if not dgram:
                l.error = 'Receive failed'
                l.done()
            else:
                if l.responder:
                    l.responder(l, dgram)
                else:
                    l.received.append(dgram)

def listen_thread():
    try:
        _listen_thread()
    except:
        pass

# test validation scaffolding

def validate_list(rcvd, expected, msg):
    if rcvd == expected:
        return True
    print ' ', msg, ':'
    i,j = 0,0
    while i < len(rcvd) and j < len(expected):
        if rcvd[i] == expected[j]:
            print 'OK:    ', hexdump(rcvd[i][0:16]), '...'
            i += 1; j += 1
        elif rcvd[i] in expected[j+1:]:
            k = j+1+expected[j+1:].index(rcvd[i])
            while j < k:
                print 'MISSED:', hexdump(expected[j][0:16]), '...'
                j += 1
        elif expected[j] in rcvd[i+1:]:
            k = i+1+rcvd[i+1:].index(expected[j])
            while i < k:
                print 'EXTRA: ', hexdump(rcvd[i][0:16]), '...'
                i += 1
        else:
            print 'WRONG: ', hexdump(rcvd[i][0:16]), '...'
            print '      [', hexdump(expected[j][0:16]), '... ]'
            i += 1
            j += 1
    for r in rcvd[i:]:
        print 'EXTRA: ', hexdump(r[0:16]), '...'
    for e in expected[j:]:
            print 'MISSED:', hexdump(e[0:16]), '...'
    return False

# generate some non-multicast MAC addresses
a1,a2 = 1,1
def getaddrs(n):
    global a1, a2
    addrs = []
    while len(addrs) < n:
        addrs.append('\0\0' + chr(a1) + '\0\0' + chr(a2))
        a2 += 1
        if a2 >= 256:
            a1,a2 = a1+1,0
    return addrs

# 'responder' function - drop spanning tree packets
stp_bcast = '\x01\x80\xc2\x00\x00\x00'
def no_bpdus(l, pkt):
    if pkt[0:6] != stp_bcast:
        l.received.append(pkt)

#------------------------------------
# now set everything up

parser = argparse.ArgumentParser(description='Test-lb - test learning bridge functionality')
parser.add_argument('--verbose', action='store_true', help='verbose printing')
parser.add_argument('--nowait', action='store_true', help='don\'t wait 30s for listening/learning states')
parser.add_argument('--tests', metavar='n[,n,...]', nargs=1, help='tests to run')
parser.add_argument('extra', nargs='*', help='[-- arg [arg...]] argument to bridge executable')
args = parser.parse_args()

b_id = '01:01:01:01:01:01'
w_args = ('./wires', '--verbose') if args.verbose else ('./wires', '--quiet') 
w = subprocess.Popen(w_args, stdout=sys.stdout)
time.sleep(1.0)
s1 = subprocess.Popen(['./bridge'] + args.extra + [b_id, '0', '1', '2'], 
                      stdout=sys.stdout, stderr=sys.stdout)
time.sleep(1.0)
if not args.nowait:
    print 'waiting for listening/learning state to expire. Use --nowait to skip'
    time.sleep(30)

passed = True

w0 = connect(0, 'testhost-0')
w1 = connect(1, 'testhost-1')
w2 = connect(2, 'testhost-2')
l0 = listener(w0, responder=no_bpdus)
l1 = listener(w1, responder=no_bpdus)
l2 = listener(w2, responder=no_bpdus)

t = threading.Thread(target=listen_thread, args=())
t.daemon = True
t.start()

#------------------------------------

def test1():
    global l0,l1,l2, w0, w1, w2
    val = True
    
    print "Test 1 - single-switch broadcast unknown"
    # three ports - wire 0, 1, 2

    payload = struct.pack('!H', 0x900) + ''.join([chr(random.randint(48,90)) for i in range(50)])
    h0,h1,h2,h3 = getaddrs(4)

    time.sleep(1.0)
    for pkt in (h1+h0+payload, h2+h3+payload):
        w0.send(pkt)
        time.sleep(1)
        val = val and validate_list(l0.pkts(), [],    'test 1 port 0')
        val = val and validate_list(l1.pkts(), [pkt], 'test 1 port 1')
        val = val and validate_list(l2.pkts(), [pkt], 'test 1 port 2')

    print 'TEST 1:', 'passed' if val else 'FAILED'
    return val

#------------------------------------

def test2():
    global l0,l1,l2, w0, w1, w2
    val = True

    print 'Test 2 - single-switch learning'
    # keep the same bridge
    h4,h5,h6 = getaddrs(3)
    payload = struct.pack('!H', 0x900) + ''.join([chr(random.randint(48,90)) for i in range(50)])

    w0.send(h4+h5+payload)       # broadcast (->h4) to w1,w2, learn w0=h5
    time.sleep(0.1)
    w2.send(h5+h4+payload)       # send (->h5) to w0, learn w2=h4
    time.sleep(0.1)
    w1.send(h4+h6+payload)       # send (->h4) to w2, learn w1=h6
    w1.send(h5+h6+payload)       # send (->h5) to w0
    time.sleep(1)

    val = val and validate_list(l0.pkts(), [h5+h4+payload,h5+h6+payload], 'test 2 port 0')
    val = val and validate_list(l1.pkts(), [h4+h5+payload], 'test 2 port 1')
    val = val and validate_list(l2.pkts(), [h4+h5+payload,h4+h6+payload], 'test 2 port 2')

    print 'TEST 2:', 'passed' if val else 'FAILED'
    return val

#------------------------------------

# packet h7->h8 in p0, out p1,p2
#        h8->h7 in p2, out p0
#  --- verify
#  --- 15s wait
#        h8->h7 in p2, out p1,p0
#  --- verify 

def test3():
    global l0,l1,l2, w0, w1, w2
    val = True

    print 'Test 3 - MAC address timeout'
    h7,h8,h9 = getaddrs(3)
    payload = struct.pack('!H', 0x900) + ''.join([chr(random.randint(48,90)) for i in range(50)])

    w0.send(h8+h7+payload)       # broadcast (->h8) to w1,w2, learn w0=h7
    time.sleep(0.1)
    w2.send(h7+h8+payload)       # send (->h7) to w0, learn w2=h8
    time.sleep(0.1)

    val = val and validate_list(l0.pkts(), [h7+h8+payload], 'test 3.1 port 0')
    val = val and validate_list(l1.pkts(), [h8+h7+payload], 'test 3.1 port 1')
    val = val and validate_list(l2.pkts(), [h8+h7+payload], 'test 3.1 port 3')

    time.sleep(16)
    w0.send(h8+h7+payload)                # broadcast to w1,w2
    time.sleep(0.1)
    w1.send(h8+h9+payload)                # broadcast to w0,w2
    time.sleep(0.1)

    val = val and validate_list(l0.pkts(), [h8+h9+payload], 'test 3.2 port 0')
    val = val and validate_list(l1.pkts(), [h8+h7+payload], 'test 3.2 port 1')
    val = val and validate_list(l2.pkts(), [h8+h7+payload, h8+h9+payload], 'test 3.2 port 3')
    
    print 'TEST 3:', 'passed' if val else 'FAILED'
    return val

    
#------------------------------------

def test4():
    global l0,l1,l2, w0, w1, w2
    val = True

    print 'Test 4 - Multiple MAC addresses per port'
    p0_addrs = getaddrs(10)
    p1_addrs = getaddrs(10)
    p2_addrs = getaddrs(10)
    bcast = '\xFF' * 6
    payload = struct.pack('!H', 0x900) + ''.join([chr(random.randint(48,90)) for i in range(50)])

    pkts = []
    for addrs,w in ((p0_addrs,w0),(p1_addrs,w1),(p2_addrs,w2)):
        for a in addrs:
            p = bcast+a+payload
            w.send(p)
            pkts.append(p)
        time.sleep(0.25)
    val = val and validate_list(l0.pkts(), pkts[10:], 'test 4.1 port 0')
    val = val and validate_list(l1.pkts(), pkts[0:10] + pkts[20:], 'test 4.1 port 1')
    val = val and validate_list(l2.pkts(), pkts[0:20], 'test 4.1 port 3')

    a0,a1,a2 = getaddrs(3)
    pkts = []
    for src,addrs,w in ((a1,p0_addrs,w1), (a2,p1_addrs,w2), (a0,p2_addrs,w0)):
        for a in addrs:
            p = a+src+payload
            w.send(p)
            pkts.append(p)
        time.sleep(0.25)
    val = val and validate_list(l0.pkts(), pkts[0:10],  'test 4.2 port 0')
    val = val and validate_list(l1.pkts(), pkts[10:20], 'test 4.2 port 1')
    val = val and validate_list(l2.pkts(), pkts[20:30], 'test 4.2 port 3')

    print 'TEST 4:', 'passed' if val else 'FAILED'
    return val
    
#------------------------------------

failed = []
passed = []

if args.tests:
    testlist = [globals()['test' + n] for n in args.tests[0].split(',')]
else:
    testlist = [test1, test2, test3, test4]

for t in testlist:
    if t():
        passed.append(t.func_name)
    else:
        failed.append(t.func_name)

print 'TESTS PASSED:', ' '.join(passed)
print 'TESTS FAILED:', ' '.join(failed) if failed else '--none--'

w.send_signal(signal.SIGINT)
s1.send_signal(signal.SIGINT)
