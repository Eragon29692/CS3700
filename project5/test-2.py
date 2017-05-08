#!/usr/bin/python
#
# test-2.py - distributed key-value store tests
#

import random, threading, subprocess
import select, time, string
import struct, socket
import signal, sys, getpass
import argparse
import posix, os

#------------------------------------


#------------------------------------
# set everything up

parser = argparse.ArgumentParser(description='Test-1 - test distributed key/value store')
parser.add_argument('--verbose', action='store_true', help='verbose printing')
parser.add_argument('--tests', metavar='n[,n,...]', nargs=1, help='tests to run')
parser.add_argument('extra', nargs='*', help='[-- arg [arg...]] argument to proj5 executable')
args = parser.parse_args()

b_args = ('./bus', '--verbose') if args.verbose else ('./bus', '--quiet')
bus = subprocess.Popen(b_args, stdout=sys.stdout)
time.sleep(1.0)


#-------------------------------------
# client implementation

fmt = ('To: %d\n' +
       'From: 8\n' +
       'Cmd: %s\n' + 
       'Id: %d\n' +
       'Key: %s\n' +
       'Value: %s')
seq = 100

def client(dst, cmd, key, value):
    global seq
    msg = fmt % (dst, cmd, seq, key, value)
    seq += 1
    s = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    if s.connect_ex('\0%s.bus.8' % getpass.getuser()):
        print 'connection error'
        return None
    s.send(msg)

    retval = None
    ready = select.select([s], [], [], 4.0)
    if not ready[0]:
        retval = '*timeout*'
    else:
        m = s.recv(4096)
        status = m.split()[5]
        if status == 'ok':
            retval = m[m.find('Value:')+7:]
        else:
            retval = '*fail*'
    s.close()
    if cmd == 'put':
        time.sleep(0.05)
    return retval

client_node = 0
def rclient(cmd, key, value):
    global client_node
    client_node = random.randint(0,7)
    return client(client_node, cmd, key, value)

#-------------------------------------
# random keys and values

def rkey():
    n = random.randint(5,15)
    return ''.join([chr(ord('a')+random.randint(0,25)) for i in range(n)])

def rvalue():
    return ' '.join([rkey() for i in range(random.randint(4,10))])

random.seed(1001)                         # deterministic random values

#-------------------------------------

nodes = [None] * 8
files = [None] * 8

# trying to kill all the error messages on shutdown - doesn't full work yet
def start_node(i):
    global nodes, files
    files[i] = os.fdopen(posix.dup(sys.stdout.fileno()), 'w')
    nodes[i] = subprocess.Popen(['./proj5'] + args.extra + ["%d" % i], stdout=files[i], stderr=files[i])
    time.sleep(0.05)

def stop_node(i):
    global nodes, files
    files[i].close()
    nodes[i].send_signal(signal.SIGINT)
    nodes[i] = None

for i in range(8):
    start_node(i)

#------------------------------------
def test1():
    print 'Test 1 - put/get functionality, 8 nodes'
    passed = True

    vals = dict([(rkey(), rvalue()) for i in range(20)])
    for k,v in vals.items():
        rclient('put', k, v)
    time.sleep(0.5)
    
    keys = vals.keys()
    random.shuffle(keys)
    for k in keys:
        v = vals[k]
        rv = rclient('get', k, '')
        if v != rv:
            print 'sent get(%s) to %d, got "%s" (not "%s")' % (k, client_node, rv, v)
            passed = False

    print 'TEST 1:', 'passed' if passed else 'FAILED'
    return passed

#------------------------------------
def test2():
    print 'Test 2 - put/get functionality, 4 nodes [0,1,4,6]'
    passed = True

    good_nodes = [0, 1, 4, 6]
    print '*** shutting down nodes (ignore error messages) ***'
    for i in range(8):
        if i not in good_nodes:
            stop_node(i)
    time.sleep(0.5)
    print '*** done shutting down nodes ***'

    vals = dict([(rkey(), rvalue()) for i in range(10)])
    for k,v in vals.items():
        n = random.choice(good_nodes)
        client(n, 'put', k, v)
    time.sleep(0.5)
    
    keys = vals.keys()
    random.shuffle(keys)
    for k in keys:
        v = vals[k]
        n = random.choice(good_nodes)
        rv = client(n, 'get', k, '')
        if v != rv:
            print 'sent get(%s) to %d, got "%s" (not "%s")' % (k, n, rv, v)
            passed = False

    print 'TEST 2:', 'passed' if passed else 'FAILED'
    return passed

#------------------------------------
def test3():
    print 'Test 3 - reload'
    passed = True

    for i in range(8):
        if not nodes[i]:
            start_node(i)
    time.sleep(0.5)

    vals = dict([(rkey(), rvalue()) for i in range(10)])
    for k,v in vals.items():
        rclient('put', k, v)
    time.sleep(0.5)

    print '*** shutting down nodes 0,2,4,6 (ignore error messages) ***'
    for i in (0,2,4,6):
        stop_node(i)
    time.sleep(1.0)
    print '*** done shutting down nodes ***'

    print 'Checking values on 1,3,5,7'
    keys = vals.keys()
    random.shuffle(keys)
    for k in keys:
        v = vals[k]
        n = random.choice((1,3,5,7))
        rv = client(n, 'get', k, '')
        if v != rv:
            print 'sent get(%s) to %d, got "%s" (not "%s")' % (k, n, rv, v)
            passed = False

    print 'starting nodes 0,2,4,6'
    for i in (0,2,4,6):
        start_node(i)
    print 'waiting for reload to complete'
    time.sleep(10)

    print '*** shutting down nodes 1,3,5,7 (ignore error messages) ***'
    for i in (1,3,5,7):
        stop_node(i)
    time.sleep(1.0)
    print '*** done shutting down nodes ***'
    
    print 'Checking values on 0,2,4,6'
    keys = vals.keys()
    random.shuffle(keys)
    for k in keys:
        v = vals[k]
        n = random.choice((0,2,4,6))
        rv = client(n, 'get', k, '')
        if v != rv:
            print 'sent get(%s) to %d, got "%s" (not "%s")' % (k, n, rv, v)
            passed = False
    
    print 'TEST 3:', 'passed' if passed else 'FAILED'
    return passed

#------------------------------------

failed = []
passed = []

if args.tests:
    testlist = [globals()['test' + n] for n in args.tests[0].split(',')]
else:
    testlist = [test1, test2, test3]

try:
    for t in testlist:
        if t():
            passed.append(t.func_name)
        else:
            failed.append(t.func_name)
except:
    pass

print 'TESTS PASSED:', ' '.join(passed)
print 'TESTS FAILED:', ' '.join(failed) if failed else '--none--'

print '*** shutting down... (ignore error messages) ***'
bus.send_signal(signal.SIGINT)
for n in nodes:
    if n:
        n.send_signal(signal.SIGINT)
print '...done'





