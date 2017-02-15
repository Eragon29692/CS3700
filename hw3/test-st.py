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
        rfds,ign1,ign2 = select.select([x.sock for x in listeners], [], [], 0.1)
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
    i, val = 0, True
    while i < min(len(rcvd),len(expected)):
        r,e = rcvd[i], expected[i]
        if r != e:
            print msg, 'received:', hexdump(r[0:16])
            print '                expected:', hexdump(e[0:16])
            val = False
        i += 1
    if i < len(rcvd):
        print msg, 'received extra messages:'
        for m in rcvd[i:]:
            print '  ', hexdump(m[0:16])
        val = False
    if i < len(expected):
        print msg, 'missing messages:'
        for m in expected[i:]:
            print '  ', hexdump(m[0:16])
        val = False
    return val

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
bcast = '\xFF\xFF\xFF\xFF\xFF\xFF'
stp_bcast = '\x01\x80\xc2\x00\x00\x00'
def no_bpdus(l, pkt):
    if pkt[0:6] != stp_bcast:
        l.received.append(pkt)

#------------------------------------
# now set everything up

parser = argparse.ArgumentParser(description='Test-lb - test learning bridge functionality')
parser.add_argument('--verbose', action='store_true', help='verbose printing')
parser.add_argument('--tests', metavar='n[,n,...]', nargs=1, help='tests to run')
parser.add_argument('extra', nargs='*', help='[-- arg [arg...]] argument to bridge executable')
args = parser.parse_args()

w_args = ('./wires', '--verbose') if args.verbose else ('./wires', '--quiet') 
w = subprocess.Popen(w_args, stdout=sys.stdout)
time.sleep(1.0)

w0,w1,w2 = connect(0, 'testhost-0'), connect(1, 'testhost-1'), connect(2, 'testhost-2')

t = threading.Thread(target=listen_thread, args=())
t.daemon = True
t.start()

def start_bridge(b_id):
    return subprocess.Popen(['./bridge'] + args.extra + [b_id, '0', '1', '2'], 
                            stdout=sys.stdout,stderr=sys.stdout)
def stop_bridge(bproc):
    bproc.send_signal(signal.SIGINT)
    bproc.wait()


#------------------------------------
# test 1 - no neighbors, all ports go through listening,learning,forwarding

def test1():
    global w0, w1, w2
    val = True

    print 'Test 1 - verify listening,learning,forwarding states'
    payload = struct.pack('!H', 0x900) + ''.join([chr(random.randint(48,90)) for i in range(50)])
    a,b,c,d,e,f,x,y,z = getaddrs(9)

    l0,l1,l2 = listener(w0,no_bpdus), listener(w1,no_bpdus), listener(w2,no_bpdus)

    bridge_pid = start_bridge('01:01:01:01:01:01')

    time.sleep(10)
    print ' .. sending frames in listening state'
    w0.send(d + a + payload)
    w1.send(e + b + payload)
    w2.send(f + c + payload)
    time.sleep(0.1)
    val = val and validate_list(l0.pkts(), [], 'test 1.1 port 0')
    val = val and validate_list(l1.pkts(), [], 'test 1.1 port 1')
    val = val and validate_list(l2.pkts(), [], 'test 1.1 port 2')
    
    time.sleep(15)
    print ' .. sending frames in learning state'
    w0.send(a + d + payload)
    w1.send(b + e + payload)
    w2.send(c + f + payload)
    time.sleep(0.1)
    val = val and validate_list(l0.pkts(), [], 'test 1.2 port 0')
    val = val and validate_list(l1.pkts(), [], 'test 1.2 port 1')
    val = val and validate_list(l2.pkts(), [], 'test 1.2 port 2')

    time.sleep(8)
    print ' .. sending frames in forwarding state'
    w2.send(a+x+payload);     time.sleep(0.01)
    w0.send(b+y+payload);     time.sleep(0.01)
    w1.send(c+z+payload)
    time.sleep(0.1)
    val = val and validate_list(l0.pkts(), [a+x+payload,c+z+payload], 'test 1.3 port 0')
    val = val and validate_list(l1.pkts(), [a+x+payload,b+y+payload], 'test 1.3 port 1')
    val = val and validate_list(l2.pkts(), [b+y+payload,c+z+payload], 'test 1.3 port 2')

    w2.send(d+x+payload)
    w0.send(e+y+payload)
    w1.send(f+z+payload)
    time.sleep(0.1)
    val = val and validate_list(l0.pkts(), [d+x+payload], 'test 1.4 port 0')
    val = val and validate_list(l1.pkts(), [e+y+payload], 'test 1.4 port 1')
    val = val and validate_list(l2.pkts(), [f+z+payload], 'test 1.4 port 2')

    w0.send(x+d+payload)
    w1.send(y+e+payload)
    w2.send(z+f+payload)
    time.sleep(0.1)
    val = val and validate_list(l0.pkts(), [y+e+payload], 'test 1.5 port 0')
    val = val and validate_list(l1.pkts(), [z+f+payload], 'test 1.5 port 1')
    val = val and validate_list(l2.pkts(), [x+d+payload], 'test 1.5 port 2')

    stop_bridge(bridge_pid)
    l0.done(); l1.done(); l2.done()

    print 'TEST 1:', 'passed' if val else 'FAILED'
    return val

def print_error(pkt, p):
    if not p:
        print 'no packet received'
        return
    for _p,q,msg in ((p,pkt,'received'), (pkt,p,'expected')):
        for i in range(0, len(_p), 16):
            print msg, ':', ' '.join(['%02x' % ord(x) for x in _p[i:i+16]])
            if _p[i:i+16] != q[i:i+16]:
                z = ' '.join(['  ' if _p[j] == q[j] else '^^' for j in range(i,min(i+16,len(_p),len(q)))])
                print ' ' * len(msg), ' ', z
            msg = ' ' * len(msg)

def ether_ntoa(n):
    return ':'.join(['%02x' % ord(x) for x in n[:]])

#------------------------------------
# test 2 - send out appropriate initial BPDUs

def test2():
    global w0, w1, w2
    val = True

    print 'Test 2 - intitial BPDU content'

    l0,l1,l2 = listener(w0), listener(w1), listener(w2)
    b_id = ''.join([chr(x) for x in [00] + [random.randint(0, 255) for i in range(5)]])
    bcast = '\x01\x80\xc2\x00\x00\x00'
    
    b = start_bridge(ether_ntoa(b_id))
    time.sleep(8)
    
    for l,port in ((l0,0),(l1,1),(l2,2)):
        pkt = (bcast + b_id + '\x00\x26\x42\x42\x03\x00\x00\x00\x00\x00\x80\x00' + b_id + 
               '\x00\x00\x00\x00\x80\x00' + b_id + '\x00' + chr(port) + '\x00\x00\x14\x00\x02\x00\x0f\x00' +
               '\0\0\0\0\0\0\0\0')
        pkts = l.pkts()
        if not pkts:
            val = False
            print ' port', port, ': no BPDUs received'
        else:
            for p in pkts:
                if p != pkt:
                    print 'port', port, ': received incorrect packet'
                    print_error(pkt, p)
                    val = False

    stop_bridge(b)
    l0.done(); l1.done(); l2.done()

    print 'TEST 2:', 'passed' if val else 'FAILED'
    return val

#------------------------------------
# test 3 - accept better root advertisements

def test3():
    global w0, w1, w2
    val = True

    print 'Test 3 - accept better root advertisements'

    l0,l1,l2 = listener(w0), listener(w1), listener(w2)
    b_id = ''.join([chr(x) for x in [8] + [random.randint(0, 255) for i in range(5)]])
    
    b = start_bridge(ether_ntoa(b_id))
    time.sleep(4)

    for l in (l0,l1,l2):
        l.pkts()                          # flush received list

    print '  neighbor root: 02:02:02:02:02:02'
    # first a neighbor that's better, on port 0
    # root ID=02:02..., cost=0, bridge ID=02:..., age=0
    pkt = ('\x01\x80\xc2\x00\x00\x00\x02\x02\x02\x02\x02\x02\x00\x26\x42\x42\x03\x00\x00\x00\x00\x00\x80\x00' +
           '\x02\x02\x02\x02\x02\x02\x00\x00\x00\x00\x80\x00\x02\x02\x02\x02\x02\x02\x00\x00' +
           '\x00\x00\x14\x00\x02\x00\x0f\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    w0.send(pkt)
    time.sleep(4)

    for i,l in ((0,l0),(1,l1),(2,l2)):
        rcvd = l.pkts()[-1]
        # root=02:.. cost=10 bridge_id = b_id port=<i> age=2.0
        xpctd = ('\x01\x80\xc2\x00\x00\x00' + b_id + '\x00\x26\x42\x42\x03\x00\x00\x00\x00\x00\x80\x00' +
                 '\x02\x02\x02\x02\x02\x02\x00\x00\x00\x0A\x80\x00' + b_id + '\x00' + chr(i) + 
                 '\x02\x00\x14\x00\x02\x00\x0f\x00\x00\x00\x00\x00\x00\x00\x00\x00')
        #          ^^^^^^^ msg_age - bytes 44 and 45
        if rcvd[0:44] != xpctd[0:44] or rcvd[46:] != xpctd[46:]:
            print 'port', i, ': received bad BPDU:'
            print_error(xpctd, rcvd) 
            val = False

    print '  remote root: 01:01:01:01:01:01'
    # now a better root at cost 30, on port 1
    # root ID=01:01..., cost=30, bridge ID=04:04..., age=4.0
    pkt = ('\x01\x80\xc2\x00\x00\x00\x04\x04\x04\x04\x04\x04\x00\x26\x42\x42\x03\x00\x00\x00\x00\x00\x80\x00' +
           '\x01\x01\x01\x01\x01\x01\x00\x00\x00\x1e\x80\x00\x04\x04\x04\x04\x04\x04\x00\x00' +
           '\x08\x00\x14\x00\x02\x00\x0f\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    w0.send(pkt)
    time.sleep(4)

    for i,l in ((0,l0),(1,l1),(2,l2)):
        rcvd = l.pkts()[-1]
        # root=02:.. cost=10 bridge_id = b_id port=<i> age=2.0
        xpctd = ('\x01\x80\xc2\x00\x00\x00' + b_id + '\x00\x26\x42\x42\x03\x00\x00\x00\x00\x00\x80\x00' +
                 '\x01\x01\x01\x01\x01\x01\x00\x00\x00\x28\x80\x00' + b_id + '\x00' + chr(i) + 
                 '\x0a\x00\x14\x00\x02\x00\x0f\x00\x00\x00\x00\x00\x00\x00\x00\x00')
        #          ^^^^^^^ msg_age - bytes 44 and 45
        if rcvd[0:44] != xpctd[0:44] or rcvd[46:] != xpctd[46:]:
            print 'port', i, ': received bad BPDU:'
            print_error(xpctd, rcvd) 
            val = False
            
    print '  better path to: 01:01:01:01:01:01'
    # same root at cost 20, on port 2
    # root ID=01:01..., cost=20, bridge ID=05:05..., age=xxx
    pkt = ('\x01\x80\xc2\x00\x00\x00\x05\x05\x05\x05\x05\x05\x00\x26\x42\x42\x03\x00\x00\x00\x00\x00\x80\x00' +
           '\x01\x01\x01\x01\x01\x01\x00\x00\x00\x14\x80\x00\x05\x05\x05\x05\x05\x05\x00\x00' +
           '\x07\x00\x14\x00\x02\x00\x0f\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    w0.send(pkt)
    time.sleep(4)

    for i,l in ((0,l0),(1,l1),(2,l2)):
        rcvd = l.pkts()[-1]
        # root=01:.. cost=30 bridge_id = b_id port=<i> age=xxx
        xpctd = ('\x01\x80\xc2\x00\x00\x00' + b_id + '\x00\x26\x42\x42\x03\x00\x00\x00\x00\x00\x80\x00' +
                 '\x01\x01\x01\x01\x01\x01\x00\x00\x00\x1e\x80\x00' + b_id + '\x00' + chr(i) + 
                 '\x08\x00\x14\x00\x02\x00\x0f\x00\x00\x00\x00\x00\x00\x00\x00\x00')
        #          ^^^^^^^ msg_age - bytes 44 and 45
        if rcvd[0:44] != xpctd[0:44] or rcvd[46:] != xpctd[46:]:
            print 'port', i, ': received bad BPDU:'
            print_error(xpctd, rcvd) 
            val = False

    stop_bridge(b)
    l0.done(); l1.done(); l2.done()

    print 'TEST 3:', 'passed' if val else 'FAILED'
    return val

#------------------------------------

def timed_pkt(l, pkt):
    l.received.append((pkt, time.time()))

def test4():
    global w0, w1, w2
    val = True

    print 'Test 4 - msg_age handling'

    l0,l1,l2 = listener(w0,timed_pkt), listener(w1,timed_pkt), listener(w2,timed_pkt)
    b_id = ''.join([chr(x) for x in [8] + 
                    [random.randint(0, 255) for i in range(5)]])
    
    b = start_bridge(ether_ntoa(b_id))
    time.sleep(4)

    # flush received list
    for l in (l0,l1,l2):
        l.pkts()    


    # rcv BPDU with msg_age=0, test that outgoing msg_age is 1 + time since reception
    # root ID=02:02..., cost=0, bridge ID=02:..., age=0
    pkt = ('\x01\x80\xc2\x00\x00\x00\x02\x02\x02\x02\x02\x02\x00\x26\x42\x42\x03\x00\x00\x00\x00\x00\x80\x00' +
           '\x02\x02\x02\x02\x02\x02\x00\x00\x00\x00\x80\x00\x02\x02\x02\x02\x02\x02\x00\x00' +
           '\x00\x00\x14\x00\x02\x00\x0f\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    t0 = time.time()
    w0.send(pkt)
    time.sleep(8)

    for i,l in ((0,l0),(1,l1),(2,l2)):
        for pkt,t in l.pkts():
            expected_time = (t-t0) + 1.0
            pkt_time = ord(pkt[44]) + ord(pkt[45])/256.0

            if abs(pkt_time - expected_time) > 1.5:
                print 'ERROR: msg_age %.2f (not %d.0)' % (pkt_time, expected_time)
                expected_pkt = (pkt[0:44] + chr(int(expected_time)) + '\0' + pkt[46:])
                print_error(expected_pkt, pkt)
                val = False


    # now send root BPDU with msg_age=8, verify outgoing msg_age
    # root ID=01:02..., cost=0, bridge ID=02:..., age=8.0
    pkt = ('\x01\x80\xc2\x00\x00\x00\x02\x02\x02\x02\x02\x02\x00\x26\x42\x42\x03\x00\x00\x00\x00\x00\x80\x00' +
           '\x01\x02\x02\x02\x02\x02\x00\x00\x00\x00\x80\x00\x02\x02\x02\x02\x02\x02\x00\x00' +
           '\x08\x00\x14\x00\x02\x00\x0f\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    t0 = time.time()
    w1.send(pkt)
    time.sleep(0.1)                       # first get rid of any sort-of-simultaneous packets
    for l in (l0,l1,l2):
        l.pkts()    
    
    time.sleep(8)
    
    for i,l in ((0,l0),(1,l1),(2,l2)):
        for pkt,t in l.pkts():
            expected_time = (t-t0) + 9.0
            pkt_time = ord(pkt[44]) + ord(pkt[45])/256.0

            if abs(pkt_time - expected_time) > 1.5:
                print 'ERROR: msg_age %.2f (not %d.0)' % (pkt_time, expected_time)
                expected_pkt = (pkt[0:44] + chr(int(expected_time)) + '\0' + pkt[46:])
                print_error(expected_pkt, pkt)
                val = False

    stop_bridge(b)
    l0.done(); l1.done(); l2.done()

    print 'TEST 4:', 'passed' if val else 'FAILED'
    return val

#------------------------------------

def last(l):
    return l[-1] if l else None

def test5():
    global w0, w1, w2
    val = True

    print 'Test 5 - time out root information'

    l0,l1,l2 = listener(w0), listener(w1), listener(w2)
    b_id = ''.join([chr(x) for x in [8] + [random.randint(0, 255) for i in range(5)]])
    
    b = start_bridge(ether_ntoa(b_id))
    time.sleep(4)

    print '  neighbor root: 02:02:02:02:02:02 age=10.0'
    # first a neighbor that's better, on port 0
    # root ID=02:02..., cost=0, bridge ID=02:..., age=0
    pkt = ('\x01\x80\xc2\x00\x00\x00\x02\x02\x02\x02\x02\x02\x00\x26\x42\x42\x03\x00\x00\x00\x00\x00\x80\x00' +
           '\x02\x02\x02\x02\x02\x02\x00\x00\x00\x00\x80\x00\x02\x02\x02\x02\x02\x02\x00\x00' +
           '\x0A\x00\x14\x00\x02\x00\x0f\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    w0.send(pkt)

    time.sleep(10)
    for l in (l0,l1,l2):
        l.pkts()                          # flush received list

    time.sleep(4)
    for i,l in ((0,l0),(1,l1),(2,l2)):
        rcvd = last(l.pkts())
        # root=02:.. cost=10 bridge_id = b_id port=<i> age=2.0
        xpctd = ('\x01\x80\xc2\x00\x00\x00' + b_id + 
                 '\x00\x26\x42\x42\x03\x00\x00\x00\x00\x00\x80\x00' + b_id + 
                 '\x00\x00\x00\x00\x80\x00' + b_id + '\x00' + chr(i) + 
                 '\x00\x00\x14\x00\x02\x00\x0f\x00' + '\0\0\0\0\0\0\0\0')

        if rcvd != xpctd:
            print 'port', i, ': received bad BPDU:'
            print_error(xpctd, rcvd)            
            val = False

    print '  remote root: 01:01:01:01:01:01'
    # now a better root at cost 30, on port 1
    # root ID=01:01..., cost=30, bridge ID=04:04..., age=4.0
    pkt = ('\x01\x80\xc2\x00\x00\x00\x04\x04\x04\x04\x04\x04\x00\x26\x42\x42\x03\x00\x00\x00\x00\x00\x80\x00' +
           '\x01\x01\x01\x01\x01\x01\x00\x00\x00\x1e\x80\x00\x04\x04\x04\x04\x04\x04\x00\x00' +
           '\x08\x00\x14\x00\x02\x00\x0f\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    w0.send(pkt)
    time.sleep(4)

    for i,l in ((0,l0),(1,l1),(2,l2)):
        rcvd = last(l.pkts())
        # root=02:.. cost=10 bridge_id = b_id port=<i> age=2.0
        xpctd = ('\x01\x80\xc2\x00\x00\x00' + b_id + '\x00\x26\x42\x42\x03\x00\x00\x00\x00\x00\x80\x00' +
                 '\x01\x01\x01\x01\x01\x01\x00\x00\x00\x28\x80\x00' + b_id + '\x00' + chr(i) + 
                 '\x0a\x00\x14\x00\x02\x00\x0f\x00\x00\x00\x00\x00\x00\x00\x00\x00')
        #          ^^^^^^^ msg_age - bytes 44 and 45
        if rcvd[0:44] != xpctd[0:44] or rcvd[46:] != xpctd[46:]:
            print 'port', i, ': received bad BPDU:'
            print_error(xpctd, rcvd)            
            
    print '  better path to: 01:01:01:01:01:01'
    # same root at cost 20, on port 2
    # root ID=01:01..., cost=20, bridge ID=05:05..., age=xxx
    pkt = ('\x01\x80\xc2\x00\x00\x00\x05\x05\x05\x05\x05\x05\x00\x26\x42\x42\x03\x00\x00\x00\x00\x00\x80\x00' +
           '\x01\x01\x01\x01\x01\x01\x00\x00\x00\x14\x80\x00\x05\x05\x05\x05\x05\x05\x00\x00' +
           '\x07\x00\x14\x00\x02\x00\x0f\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    w0.send(pkt)
    time.sleep(4)

    for i,l in ((0,l0),(1,l1),(2,l2)):
        rcvd = l.pkts()[-1]
        # root=01:.. cost=30 bridge_id = b_id port=<i> age=xxx
        xpctd = ('\x01\x80\xc2\x00\x00\x00' + b_id + '\x00\x26\x42\x42\x03\x00\x00\x00\x00\x00\x80\x00' +
                 '\x01\x01\x01\x01\x01\x01\x00\x00\x00\x1e\x80\x00' + b_id + '\x00' + chr(i) + 
                 '\x08\x00\x14\x00\x02\x00\x0f\x00\x00\x00\x00\x00\x00\x00\x00\x00')
        #          ^^^^^^^ msg_age - bytes 44 and 45
        if rcvd[0:44] != xpctd[0:44] or rcvd[46:] != xpctd[46:]:
            print 'port', i, ': received bad BPDU:'
            print_error(xpctd, rcvd)            

    stop_bridge(b)
    l0.done(); l1.done(); l2.done()

    print 'TEST 5:', 'passed' if val else 'FAILED'
    return val

#------------------------------------

def test6():
    global w0, w1, w2
    val = True

    print 'Test 6 - blocked port test'

    l0,l1,l2 = listener(w0, no_bpdus), listener(w1,no_bpdus), listener(w2,no_bpdus)
    b_id = ''.join([chr(x) for x in [8] + [random.randint(0, 255) for i in range(5)]])
    
    bproc = start_bridge(ether_ntoa(b_id))

    # root 02:02... cost 0 bridge 02:02...
    bpdu2 = ('\x01\x80\xc2\x00\x00\x00\x02\x02\x02\x02\x02\x02\x00\x26\x42\x42\x03\x00\x00\x00\x00\x00\x80\x00' +
             '\x02\x02\x02\x02\x02\x02\x00\x00\x00\x00\x80\x00\x02\x02\x02\x02\x02\x02\x00\x00' +
             '\x00\x00\x14\x00\x02\x00\x0f\x00\x00\x00\x00\x00\x00\x00\x00\x00')
    # root 02:02... cost 10 bridge 03:03...
    bpdu3 = ('\x01\x80\xc2\x00\x00\x00\x02\x02\x02\x02\x02\x02\x00\x26\x42\x42\x03\x00\x00\x00\x00\x00\x80\x00' +
             '\x02\x02\x02\x02\x02\x02\x00\x00\x00\x0a\x80\x00\x03\x03\x03\x03\x03\x03\x00\x00' +
             '\x02\x00\x14\x00\x02\x00\x0f\x00\x00\x00\x00\x00\x00\x00\x00\x00')

    print '  root on port 0, block port 1'
    for i in range(20):
        w0.send(bpdu2)
        w1.send(bpdu3)
        time.sleep(2)

    payload = struct.pack('!H', 0x900) + ''.join([chr(random.randint(48,90)) for i in range(50)])
    a,b,c,d,e,f,x,y,z = getaddrs(9)

    w0.send(d + a + payload); time.sleep(0.05)
    w1.send(e + b + payload); time.sleep(0.05)
    w2.send(f + c + payload)
    time.sleep(0.1)
    val = val and validate_list(l0.pkts(), [f+c+payload], 'test 6.1 port 0')
    val = val and validate_list(l1.pkts(), [], 'test 6.1 port 1')
    val = val and validate_list(l2.pkts(), [d+a+payload], 'test 6.1 port 2')

    stop_bridge(bproc)
    l0.done(); l1.done(); l2.done()

    print 'TEST 6:', 'passed' if val else 'FAILED'
    return val

#------------------------------------

crashed = False
failed = []
passed = []

if args.tests:
    testlist = [globals()['test' + n] for n in args.tests[0].split(',')]
else:
    testlist = [test1,test2,test3,test4,test5,test6]
#try:
if True:
    for t in testlist:
        if t():
            passed.append(t.func_name)
        else:
            failed.append(t.func_name)
            alldone = True
# except Exception as e:
#     print 'exception:', e
#     crashed = True

print 'TESTS PASSED:', ' '.join(passed)
print 'TESTS FAILED:', ' '.join(failed) if failed else '--none--'
if crashed:
    print 'Warning: failure during testing, not all tests completed'

w.send_signal(signal.SIGINT)
