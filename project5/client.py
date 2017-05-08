#!/usr/bin/python

import sys
import socket
import getpass
import argparse
import posix
import select

parser = argparse.ArgumentParser(description='client - send request')
parser.add_argument('dest', metavar='<n>', type=int, nargs=1,
                    help='target node number')
parser.add_argument('cmd', metavar='put/get', type=str, nargs=1)
parser.add_argument('key', metavar='key', type=str, nargs=1)
parser.add_argument('val', metavar='[value]', type=str, nargs='?', default='')
parser.add_argument('--test', action='store_true', help='test it')

fmt = ('To: %d\n' +
       'From: 8\n' +
       'Cmd: %s\n' + 
       'Id: %d\n' +
       'Key: %s\n' +
       'Value: %s')

if __name__ == '__main__':
    args = parser.parse_args()

    if not args.test:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        if s.connect_ex('\0%s.bus.8' % getpass.getuser()):
            print 'connection error'
            sys.exit(1)
    msg = fmt % (args.dest[0], args.cmd[0], posix.getpid(), args.key[0], args.val)
    if args.test:
        print msg
    else:
        s.send(msg)

    ready = select.select([s], [], [], 4.0)
    if ready[0]:
        m = s.recv(4096)
        print m
    else:
        print '*** no reply ***'

    
