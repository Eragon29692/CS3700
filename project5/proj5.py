#!/usr/bin/python
#
# simple program to connect to message bus and send messages
#

import sys
import socket
import time
import threading
import string
import getpass
import argparse

parser = argparse.ArgumentParser(description='example - send messages on message bus')
parser.add_argument('nodeid', metavar='n', type=int, nargs=1,
                    help='Node ID')
args = parser.parse_args()

nodeidInt = args.nodeid[0]
nodeid = str(nodeidInt)

fmt = ('To: %d\n' + 'From: %d\n' + 'Cmd: %s\n' + 'Id: %d\n' +'Key: %s\n' + 'Value: %s')

 
#class to represent HTTPMessage
class HTTPMessage:
    def __init__(self, toNode, fromNode, cmd, messageId, key = '', value = ''):
        self.toNode = toNode
        self.fromNode = fromNode
        self.cmd = cmd
        self.messageId = messageId
        self.key = key
        self.value = value

    def sendMessage(self):
        fmt = ('To: %d\n' + 'From: %d\n' + 'Cmd: %s\n' + 'Id: %d\n' +'Key: %s\n' + 'Value: %s')
        return fmt % (int(self.toNode), int(nodeid), self.cmd, int(self.messageId), self.key, self.value)


#return a HTTPMessage to save from a httpMessage list of Strings split(\n) in fmt format
def createMessage(httpMessage):
    return HTTPMessage(httpMessage[0][4:], httpMessage[1][6:], httpMessage[2][5:], httpMessage[3][4:], httpMessage[4][5:], httpMessage[5][7:])

#hash a key string and return which nodes (0 -> 7) the key belongs to  
def hashToNode(key):
    hashKey = sum(bytearray(key)) % 255
    nodeSend = int(hashKey/32)
    return [str(nodeSend), str(int((nodeSend + 1) % 8)), str(int((nodeSend + 2) % 8))] 

#process receives
def receive(s):
    global requestTable
    while True:
        dgram = s.recv(4096)
        if not dgram:
            print 'lost connection'
            sys.exit(1)
        print 'received:'
        for line in dgram.split('\n'):
            print ' ', line

        #process request
        httpMessage = dgram.split('\n')

        #Receive an ok request
        if (httpMessage[2] == 'Cmd: ok'):
            requestOk = createMessage(httpMessage);
            requestTable.append(requestOk)

        #Receive a fail request
        if (httpMessage[2] == 'Cmd: fail'):
            pass
        
        #Receive a store request
        if (httpMessage[2] == 'Cmd: store'):
            requestStore = createMessage(httpMessage);
            requestTable.append(requestStore)
            responseStore = HTTPMessage(requestStore.fromNode, nodeid, 'ok', requestStore.messageId)
            s.send(responseStore.sendMessage())

        #Receive a fetch request
        if (httpMessage[2] == 'Cmd: fetch'):
            requestFetch = createMessage(httpMessage);
            resultFetch = [x for x in requestTable if x.cmd == 'store' and x.key == requestFetch.key]
            resultFetchLen = len(resultFetch)
            if (resultFetchLen > 0):
                responseFetch = HTTPMessage(requestFetch.fromNode, nodeid, 'ok', requestFetch.messageId, resultFetch[resultFetchLen - 1].key, resultFetch[resultFetchLen - 1].value)
                s.send(responseFetch.sendMessage())
            if (resultFetchLen == 0):
                responseFetch = HTTPMessage(requestFetch.fromNode, nodeid, 'fail', requestFetch.messageId)
                s.send(responseFetch.sendMessage())

    
        #Receive a put request
        if (httpMessage[2] == 'Cmd: put'):
            requestPut = createMessage(httpMessage);
            t = threading.Thread(target=processPut, args=(s, requestPut,))
            t.daemon = True                   # so ^C works
            t.start()
             

        #Receive a get request
        if (httpMessage[2] == 'Cmd: get'):
            requestGet = createMessage(httpMessage);
            t = threading.Thread(target=processGet, args=(s, requestGet,))
            t.daemon = True                   # so ^C works
            t.start()


        #Receive a reload request
        if (httpMessage[2] == 'Cmd: reload'):
            requestReload = createMessage(httpMessage);
            t = threading.Thread(target=processReload, args=(s, requestReload,))
            t.daemon = True                   # so ^C works
            t.start()
         
#process put
def processPut(s, requestPut):
    global requestTable
    global seq

    failAll = True

    nodeToSend = hashToNode(requestPut.key)
    for node in nodeToSend:
        seqNum = seq
        seq += 1
        requestStore = HTTPMessage(node, nodeid, 'store', seqNum, requestPut.key, requestPut.value)
        s.send(requestStore.sendMessage())
        time.sleep(1)
        resultStore = [x for x in requestTable if (x.toNode == nodeid and x.fromNode == node and x.cmd == 'ok' and x.messageId == str(seqNum))]
        if (len(resultStore) > 0 and failAll):
            responsePut = HTTPMessage(requestPut.fromNode, nodeid, 'ok', requestPut.messageId)
            s.send(responsePut.sendMessage())
            failAll = False
    if failAll:
        responsePut = HTTPMessage(requestPut.fromNode, nodeid, 'fail', requestPut.messageId)
        s.send(responsePut.sendMessage())

#process Get            
def processGet(s, requestGet):
    global requestTable
    global seq

    failAll = True

    nodeToSend = hashToNode(requestGet.key)
    for node in nodeToSend:
        if failAll:
            seqNum = seq
            seq += 1
            requestFetch = HTTPMessage(node, nodeid, 'fetch', seqNum, requestGet.key)
            s.send(requestFetch.sendMessage())
            time.sleep(1)
            resultFetch = [x for x in requestTable if x.toNode == nodeid and x.fromNode == node and x.cmd == 'ok' and x.messageId == str(seqNum) and x.key == requestGet.key]
            if (len(resultFetch) > 0 and failAll):
                responseGet = HTTPMessage(requestGet.fromNode, nodeid, 'ok', requestGet.messageId, resultFetch[0].key, resultFetch[0].value)
                s.send(responseGet.sendMessage())
                failAll = False
    if failAll:
        responseGet = HTTPMessage(requestGet.fromNode, nodeid, 'fail', requestGet.messageId)
        s.send(responseGet.sendMessage())


#process Reload
def processReload(s, requestReload):
    global requestTable
    global seq

    resultReload = [x for x in requestTable if x.cmd == 'store' and requestReload.fromNode in hashToNode(x.key)]
    for result in resultReload:
        seqNum = seq
        seq += 1
        requestStore = HTTPMessage(requestReload.fromNode, nodeid, 'store', seqNum, result.key, result.value)
        s.send(requestStore.sendMessage())
        



if __name__ == '__main__':

    #send seq message id
    seq = 0
    #all requests are saved here
    requestTable = []

    s = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    s.bind('\0%s.test-%d' % (getpass.getuser(), nodeidInt))
    if s.connect_ex('\0%s.bus.%d' % (getpass.getuser(), nodeidInt)):
        print 'connection error'
        sys.exit(1)

    t = threading.Thread(target=receive, args=[s])
    t.daemon = True                   # so ^C works
    t.start()


    s.send(HTTPMessage(str((nodeidInt + 1) % 8), nodeid, 'reload', seq).sendMessage())
    s.send(HTTPMessage(str((nodeidInt + 2) % 8), nodeid, 'reload', seq).sendMessage())
    s.send(HTTPMessage(str((nodeidInt - 1) % 8), nodeid, 'reload', seq).sendMessage())
    s.send(HTTPMessage(str((nodeidInt - 2) % 8), nodeid, 'reload', seq).sendMessage())




    while True:
        pass
