#!/usr/bin/python
#
# test-1.py - distributed key-value store tests
#

import random, threading, subprocess
import select, time, string
import struct, socket
import signal, sys, getpass
import argparse

#------------------------------------


#------------------------------------
# set everything up

parser = argparse.ArgumentParser(description='Test-1 - test distributed key/value store')
parser.add_argument('--verbose', action='store_true', help='verbose printing')
parser.add_argument('--tests', metavar='n[,n,...]', nargs=1, help='tests to run')
parser.add_argument('extra', nargs='*', help='[-- arg [arg...]] argument to proj5 executable')
args = parser.parse_args()

b_args = ('./bus', '--verbose') if args.verbose else ('./bus')
bus = subprocess.Popen(b_args, stdout=sys.stdout)
time.sleep(1.0)

nodes = [None] * 8
for i in range(8):
    nodes[i] = subprocess.Popen(['./proj5'] + args.extra + ["%d" % i],
                                stdout=sys.stdout, stderr=sys.stdout)
time.sleep(1.0)

try:
    time.sleep(10000)
except:
    print 'shutting down...'
    bus.send_signal(signal.SIGINT)
    for n in nodes:
        n.send_signal(signal.SIGINT)
    print '...done'
