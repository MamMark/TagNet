#!/usr/bin/env python

import time
import sys
import signal
import binascii

from construct        import *
from twisted.internet import reactor, defer
from txdbus           import client, error, objects
from txdbus.interface import DBusInterface, Method, Signal
from twisted.python   import log

from tagnet import TagName, TagMessage, TagPayload, TagPoll

log.startLogging(sys.stdout)

#from tagnet import tagnet_dbus_interface

#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

msg_header_s = Struct('msg_header_s',
                    Byte('length'),
                    Byte('sequence'),
                    UBInt16('address'),
                    Enum(Byte('test_mode'),
                         DISABLED = 0,
                         RUN  = 1,
                         PEND = 2,
                         PING = 3,
                         PONG = 4,
                         REP  = 5,
                         )
                    )

#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

# global list of tags within radio range
#
taglist = dict()

#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

TAGNET_BUS_NAME = 'org.tagnet.tagnet'           # bus name for tagnet forwarder
TAGNET_OBJECT_PATH = '/org/tagnet/tagnet'

tagnet_dbus_interface = DBusInterface(TAGNET_BUS_NAME,
                                      Method('tag_list', arguments='s', returns='ay' ),
                                      Signal('tag_found', 'ay' ),  # report new tag
                                      Signal('tag_lost', 'ay' ),   # report tag out of range
                                      Signal('tag_events', 'ay' ), # report new tag events
                                      Signal('tagnet_status', 'ay' ),
                                      )

class TagNetDbus(objects.DBusObject):
    """
    provides the interface for accessing the tagnet port
    """
    dbus_interfaces = [tagnet_dbus_interface]
                 
    def __init__(self, object_path, connection):
        self.object_path = object_path
        super(TagNetDbus, self).__init__(object_path)
        self.obj_handler = objects.DBusObjectHandler(self)

    def dbus_tag_list(self, arg):
        print 'Received remote call. Argument: ', arg
        return 'You sent (%s)' % arg

    def tagnet_status(self):
        self.emitSignal('tagnet_status', bytearray('ok'))

    def tag_lost(self):
        self.emitSignal('tag_lost', bytearray('ok'))

    def tag_found(self):
        self.emitSignal('tag_found', bytearray('ok'))

    def tag_events(self):
        self.emitSignal('tag_events', bytearray('ok'))

#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

from si446x import si446x_dbus_interface

SI446X_BUS_NAME = 'org.tagnet.si446x'           # bus name for si446x device driver
SI446X_OBJECT_PATH = '/org/tagnet/si446x/0/0'   # object name includes device id/port numbers

POLL_DELAY = 5   # seconds

class Si446xComponent(object):
    def __init__(self, conn, report_changes):
        self.report_changes = report_changes
        self.conn = conn
        self.poll_count = 0
        self.recv_count = 0
        self.last_t = None
        self.msg = bytearray(('\x00' * msg_header_s.sizeof()) + 'hello world')
        self.msg[0] = len(self.msg)-1
        self.pwr = 32
        self.last_t = None
        self.this_t = None
        super(Si446xComponent, self).__init__()

    def start(self, conn):
        print 'get remote si446x object:  {}  {}'.format(SI446X_BUS_NAME, SI446X_OBJECT_PATH)
        deferred = conn.getRemoteObject(SI446X_BUS_NAME,
                                        SI446X_OBJECT_PATH,
                                        interfaces=si446x_dbus_interface)
        deferred.addCallback(self.got_remote)

    def got_remote(self, robj):
        print 'got remote si446x object {}  {}'.format(SI446X_BUS_NAME, SI446X_OBJECT_PATH)
        self.robj = robj
        robj.notifyOnSignal('receive', self.on_receive)
#        robj.notifyOnSignal('receive', self.on_receive, interface=si446x_dbus_interface)
#        robj.onError(self.on_error)
        reactor.callLater(0, self.send_poll, robj)

    def send_poll(self, robj):
        print 'send_poll'
        msg = TagPoll().build()
        print binascii.hexlify(msg)
        deferred =  robj.callRemote('send', msg, self.pwr)
        deferred.addCallback(self.poll_sent)
        print 'send packet ({}:{})'.format(self.poll_count, self.recv_count)

    def poll_sent(self, e):
        print 'poll_sent'
        self.poll_count += 1
        reactor.callLater(POLL_DELAY, self.send_poll, self.robj)

    def on_error(self, failure):
        import sys
        sys.stderr.write(str(failure))

    def on_receive(self, msg, pwr):
        print 'on_receive'
        changes = []
        self.report_changes(changes)
        self.this_t = time.time()
        self.last_t = self.last_t if (self.last_t) else time.time()
        self.last_t = self.this_t

#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

class TagNetComponent(object):
    def __init__(self, conn):
        self.conn = conn
        super(TagNetComponent, self).__init__()

    def start(self, conn):
        self.tag_obj = TagNetDbus(TAGNET_OBJECT_PATH, conn)
        conn.exportObject(self.tag_obj)
        deferred = conn.requestBusName(TAGNET_BUS_NAME)
        deferred.addCallback(self.got_bus)

    def got_bus(self, bus_id):
        self.bus_id = bus_id
        
    def on_error(self, failure):
        import sys
        sys.stderr.write(str(failure))

    def report_changes(self, changes):
        pass
        
#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

def reactor_loop():
    """
    controls the main processing loop using reactor.run()
    """
    def on_running():
        """
        called when the twisted reactor is running
        """
        print 'running'
        try:
            conn = client.connect(reactor)
            tagnet_do = TagNetComponent(conn)
            conn.addCallback(tagnet_do.start)
            conn.addErrback(tagnet_do.on_error)
            conn = client.connect(reactor)
            si446x_do = Si446xComponent(conn, tagnet_do.report_changes)
            conn.addCallback(si446x_do.start)
            conn.addErrback(si446x_do.on_error)
        except error.DBusException, e:
            print 'DBus Setup Error:', e
            reactor.stop()

    signal.signal(signal.SIGINT, SIGINT_CustomEventHandler)
    signal.signal(signal.SIGHUP, SIGINT_CustomEventHandler)
    reactor.callWhenRunning(on_running)
    reactor.run()

#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

def SIGINT_CustomEventHandler(num, frame):
    k={1:"SIGHUP", 2:"SIGINT"}
    log.msg("Recieved signal - " + k[num])
    if frame is not None:
        log.msg("SIGINT at %s:%s"%(frame.f_code.co_name, frame.f_lineno))
    log.msg("In SIGINT_CustomEventHandler")
    if num == 2:
        log.msg("shutting down ....")
        reactor.stop()
     
if __name__ == '__main__':
    reactor_loop()
