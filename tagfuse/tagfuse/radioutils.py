# coding: utf-8

# Si446x Device Direct Access Layer Access
#
# This notebook explores the Si446xRadio class, which handles the direct access to operating system provided SPI bus and GPIO interface pins that connect to the Si446x device. This provides the command and control interface provided by the device.

from __future__ import print_function
from builtins import *                  # python3 types

UNIT_TESTING = False

__all__ = ['name2version',
           'payload2values',
           'payload2special',
           'msg_exchange',
           'path2tlvs',
           'path2list',
           'radio_get_group',
           'radio_get_property',
           'radio_format_group',
           'radio_show_config',
           'radio_get_raw_config',
           'radio_receive_msg',
           'radio_send_msg',
           'radio_get_position',
           'radio_get_rssi',
           'radio_get_power',
           'radio_set_power',
           'radio_read_test',
           'radio_write_test',
           'radio_poll',
           'radio_get_rtctime',
           'radio_set_rtctime',
]

import sys
import os
import structlog
mylog = structlog.getLogger('fuse.log-mixin.tagfuse.' + __name__)
import inspect

from time import sleep
import struct as pystruct
import types
from binascii import hexlify

from pyproj import Proj, transform

# If we are running from the source package directory, try
# to load the module from there first.
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# zzz print('{} init: argv:{}, basedir:{}'.format(os.path.basename(basedir),
#                                            sys.argv[0],
#                                            basedir,))
if (os.path.exists(basedir)
    and os.path.exists(os.path.join(basedir, 'setup.py'))):
    add_dirs = [os.path.join(basedir, os.path.basename(basedir)),
                os.path.join(basedir, '../si446x'),
                os.path.join(basedir, '../tagnet')]
    for ndir in add_dirs:
        if (ndir not in sys.path):
            sys.path.insert(0,ndir)
    # zzz print '\n'.join(sys.path)

from si446x import Si446xRadio
from si446x import clr_pend_int_s
from si446x import radio_config_cmd_ids, radio_config_commands
from si446x import radio_config_group_ids, radio_config_groups
from si446x import radio_display_structs, RadioTraceIds
from si446x import get_ids_wds, get_config_wds, get_name_wds, wds_default_config

from tagnet import TagTlv, TagTlvList, tlv_types, tlv_errors
from tagnet import TagMessage, TagName
from tagnet import TagPoll, TagGet, TagPut, TagDelete, TagHead
from tagnet import TlvListBadException, TlvBadException

try:
    from tagfuseargs import get_cmd_args
except ImportError:
    from tagfuse.tagfuseargs import get_cmd_args

try:
    import si446x.monotonic as monotonic
    def time():
        return monotonic.millis()
except:
    from time import time

clr_all_flags = clr_pend_int_s.parse('\x00' * clr_pend_int_s.sizeof())
clr_no_flags  = clr_pend_int_s.parse('\xff' * clr_pend_int_s.sizeof())

# default paramters
MAX_FIFO_SIZE       = 129
MAX_WAIT            = 1000 # milliseconds
MAX_RECV            = 2
MAX_PAYLOAD         = 254
MAX_RETRIES         = 4
RADIO_POWER         = 20
SHORT_DELAY         = 100  # milliseonds


#WGS84   EPSG:4326     World Geodetic System 1984 (lat/lon)
#ECEF    EPSG:4978     SirfBin X.Y.Z
#        EPSG:3857     ??? Psuedo-Mercator Google Maps
wgs84= Proj(init='epsg:4326')
ecef = Proj(init='epsg:4978')
psdo = Proj(init='epsg:3857')

#(gdb) p GPSmonitorP__m_xyz
#$7 = {ts = 0x229927d, tow = 0x2ee8d04, x = 0xffd6c1bf, y = 0xffbe1099, z = 0x3a5104,
#           week = 0x3b4, mode1 = 0x4, hdop = 0x4, nsats = 0x8}
#(gdb) p GPSmonitorP__m_geo
#$8 = {ts = 0x2299260, tow = 0x1d518228, week_x = 0x7b4, nsats = 0x8, additional_mode = 0x18,
#           lat = 0x16153920, lon = 0xb7443e55, sat_mask = 0x51084812, nav_valid = 0x0,
#           nav_type = 0x204, ehpe = 0x377, evpe = 0x0, alt_ell = 0x3eaf, alt_msl = 0x4905,
#           sog = 0x0, cog = 0x6665, hdop = 0x4}
xyz_struct = pystruct.Struct('>iii')
lata = "16153920"
lona = "b7443e55"
elva = "00003eaf"
ba=bytearray.fromhex(lata+lona+elva)
lat, lon, elv = xyz_struct.unpack(ba)

home_geo = float(lat)/10**7, float(lon)/10**7, float(elv)/10**2
if get_cmd_args().verbosity > 3:
    mylog.debug('home geolocation', lineno=sys._getframe().f_lineno,
                data={'latitude':lat,'longitude':lon,'elevation':elv,})

xa = "ffd6c1bf"
ya = "ffbe1099"
za = "003a5104"
ba=bytearray.fromhex(xa+ya+za)
x, y, z = xyz_struct.unpack(ba)

home_xyz = x, y, z
if get_cmd_args().verbosity > 3:
    mylog.debug('home xyz location', lineno=sys._getframe().f_lineno,
                data={'x':x,'y':y,'z':z,})

# Scotts Valley
# x: -13583956.319900 y: 4445954.972893
# lat: 37°2'56.813" lon: -122°1'36.321"
# lat: 37.0491147°  lon: -122.0267558°


def name2version(name):
    '''
    convert file name to tuple of version (major,minor,build)
    return name.split('.')
    '''

def payload2special(payload, keynames):
    '''
    get first keyname to match and return its value as packed bytes
    '''
    buf = bytearray()
    if get_cmd_args().verbosity > 4:
        mylog.debug(method=inspect.stack()[0][3],
                    lineno=sys._getframe().f_lineno,
                    data=keynames.__repr__())
    for match_key in keynames:
        for tlv in payload:
            if match_key == tlv.tlv_type():
                buf = bytearray(tlv.build())
                payload.remove(tlv)
                break
            if get_cmd_args().verbosity > 4:
                mylog.debug(method=inspect.stack()[0][3],
                            lineno=sys._getframe().f_lineno,
                            data={'match':match_key, 'tlv':tlv.__repr__()})
        if buf:
            break
    if get_cmd_args().verbosity > 4:
        mylog.debug(method=inspect.stack()[0][3],
                    lineno=sys._getframe().f_lineno,
                    data='' if not buf else hexlify(buf))
    return buf


def payload2values(payload, keynames):
    '''
    Extract all parameters in payload and then filter for the
    parameters of interest.

    Remove any matched parameters from the payload.
    '''
    plist = []
    if get_cmd_args().verbosity > 3:
        mylog.debug(method=inspect.stack()[0][3],
                    lineno=sys._getframe().f_lineno,
                    data=keynames.__repr__())
    for match_key in keynames:
        item = None
        for tlv in payload:
            if match_key == tlv.tlv_type():
                item = tlv.value()
                payload.remove(tlv)
                break
            if get_cmd_args().verbosity > 5:
                mylog.debug(method=inspect.stack()[0][3],
                            lineno=sys._getframe().f_lineno,
                            data={'match':match_key, 'tlv':tlv, 'list':plist})
        plist.append(item)
    if get_cmd_args().verbosity > 3:
        mylog.debug(method=inspect.stack()[0][3],
                    lineno=sys._getframe().f_lineno,
                    data=plist.__repr__())
    return (plist)

def path2tlvs(path_list):
    '''
    Convert a list of individual elements in a path into
    a list of Tag Tlvs
    '''
    def _build_tlv(val):
        try:                                   # integer
            return TagTlv(tlv_types.INTEGER, int(val))
        except: pass
        try:                                   # string or <type:value>
            return TagTlv(val.encode('utf-8'))
        except: pass
        return TagTlv(val)

    tlist = []
    for p in path_list:
        t = _build_tlv(p)
        if (t):
            tlist.append(t)
    return tlist

def path2list(path):
    path = os.path.abspath(os.path.realpath(path))
    return path.split('/')[1:]

def msg_exchange(radio, req, power=None, wait=MAX_WAIT, tries=MAX_RETRIES):
    '''
    Send a TagNet request msg and wait for a response.

    checks for error in response and will retry three times
    if request was not successful.
    Timeouts on the transmit will also be counted as an error
    and reported appropriately.
    '''
    req_msg = req.build()
    if get_cmd_args().verbosity > 2:
        mylog.debug('start', method=inspect.stack()[0][3],
                    lineno=sys._getframe().f_lineno,
                    hdr=req.header,
                    name=req.name,
                    tries=tries,
                    size=len(req_msg),
                    sample=hexlify(req_msg[:20]))
    if get_cmd_args().verbosity > 4 and req.payload:
        mylog.debug(method=inspect.stack()[0][3],
                    lineno=sys._getframe().f_lineno,
                    data=req.payload)
    while (tries):
        error = tlv_errors.ERETRY
        payload = None
        sstatus = radio_send_msg(radio, req_msg, power)
        rsp_buf, rssi, rstatus = radio_receive_msg(radio, MAX_RECV, wait)
        if get_cmd_args().verbosity > 4 and req.payload:
            mylog.debug('msg_exchange received', method=inspect.stack()[0][3],
                        rssi=rssi, rstatus=rstatus)
        if (rsp_buf):
            if get_cmd_args().verbosity > 3:
                mylog.debug(method=inspect.stack()[0][3], lineno=sys._getframe().f_lineno,
                            size=len(rsp_buf),
                            sample=hexlify(rsp_buf[:20]))
            try:
                rsp = TagMessage(bytearray(rsp_buf))
                if (rsp.payload):
                    payload = rsp.payload
                    if get_cmd_args().verbosity > 4:
                        mylog.debug('rsp payload', method=inspect.stack()[0][3], lineno=sys._getframe().f_lineno,
                                    data=payload.__repr__())
                    error, eof = payload2values(payload,
                                           [tlv_types.ERROR,
                                            tlv_types.EOF,
                                           ])
                    if (error is None):
                        error = tlv_errors.SUCCESS
                    if (eof):
                        error = tlv_errors.EODATA
            except (ValueError, TypeError, TlvBadException, TlvListBadException):
                error = tlv_errors.EINVAL
                mylog.error('rsp exception', method=inspect.stack()[0][3],)
                pass # continue with counting this as retry
        else:
            error = tlv_errors.ETIMEOUT
            mylog.error('timeout', method=inspect.stack()[0][3],
                       error=error, tries=tries)
        if (error is tlv_errors.SUCCESS) \
           or (error is tlv_errors.EODATA) \
           or (error is tlv_errors.EALREADY):
            if get_cmd_args().verbosity > 4:
                mylog.debug('done', method=inspect.stack()[0][3], lineno=sys._getframe().f_lineno,
                            error=error,
                            tries=tries)
            break
        tries -= 1
        if get_cmd_args().verbosity > 3:
            mylog.debug('retry', method=inspect.stack()[0][3], lineno=sys._getframe().f_lineno,
                        tries=tries,
                        error=error)
        if (tries) and (error is tlv_errors.EBUSY):
            sleep(.1)
            if get_cmd_args().verbosity > 3:
                mylog.debug('sleep', method=inspect.stack()[0][3], lineno=sys._getframe().f_lineno,
                            error=error,
                            time=.1)
    if get_cmd_args().verbosity > 2:
        mylog.debug('complete', method=inspect.stack()[0][3], lineno=sys._getframe().f_lineno,
                    error=error, data=payload.__repr__())
    return error, payload, (rssi, sstatus, rstatus)


def radio_show_config(radio, config):
    '''
    Show Radio device configuration
    '''
    radio_show_config(radio.dump_radio())
    total = 0
    if get_cmd_args().verbosity > 1:
        mylog.debug('const config strings',method=inspect.stack()[0][3],
                          lineno=sys._getframe().f_lineno, )
    for s in config:
        if get_cmd_args().verbosity > 1:
            mylog.debug(method=inspect.stack()[0][3],
                        lineno=sys._getframe().f_lineno,
                        data=(hexlify(s)))
        total += len(s) - 4
    if get_cmd_args().verbosity > 1:
        mylog.debug(method=inspect.stack()[0][3],
                    lineno=sys._getframe().f_lineno,
                    size=total)
    # ## Get Chip Status
    if get_cmd_args().verbosity > 1:
        mylog.debug('const config strings',method=inspect.stack()[0][3],
                    lineno=sys._getframe().f_lineno,
                    data=radio.get_chip_status())

# Get Radio Property Group

def radio_get_group(radio, g_n):
    g_s = radio_config_groups[radio_config_group_ids.build(g_n)]
    return g_s.parse(radio_get_property(radio, g_n, 0, g_s.sizeof()))


# Get Radio Property

def radio_get_property(radio, g_n, start, limit):
    prop_x = 0
    prop_b = bytearray()
    while (prop_x < limit):
        chunk_size = limit - prop_x
        x = MAX_RADIO_RSP if (chunk_size >= MAX_RADIO_RSP) else chunk_size
        rsp = radio.get_property(g_n, prop_x, x)
        if (rsp):
            prop_b += bytearray(rsp[:x])
            prop_x += x
        else:
            mylog.info('failure',method=inspect.stack()[0][3])
            raise RuntimeError('radio_start: radio config command error')
            # return None
    return prop_b


# Format Radio Property Group

def radio_format_group(gn, data):
    s = ' {} '.format(gn)
    try:
        my_struct = radio_config_groups[radio_config_group_ids.build(gn)]
        p = radio_display_structs[my_struct]
        s += p(my_struct, data)
    except:
        if ((s_name == 'string') or isinstance(data, types.StringType)):
            s += data
        else:
            s += insert_space(hexlify(data))
    return  s


#  Show Radio Configuration

def radio_show_config(config):
    total = 0
    for k, v in config.iteritems():
        total += len(v)
        s = radio_config_groups[k]
        p = radio_display_structs[s]
        print('\n{}: {}\n{}'.format(s.name, s.sizeof(), insert_space(v)))
        print(p(s,v))
    print('\n=== total: {}'.format(total))


# Get Compiled Radio Configuration

def radio_get_raw_config():
    rl = []
    for l in [get_config_wds, get_config_device]:
        x = 0
        while (True):
            s = l(x)
            if (not s): break
            rl.append(s)
            x += len(s) + 1
    return rl


# Get Radio Interrupt Information

def int_status(radio, clr_flags, show=False):
    clr_flags.ph_pend.STATE_CHANGE = False    # always clear this interrupt
    if get_cmd_args().verbosity > 4:
        mylog.debug(method=inspect.stack()[0][3], lineno=sys._getframe().f_lineno,
                    flags=clr_flags, show=show)
    try:
        p_g = radio.get_clear_interrupts(clr_flags)
    except Exception as ex:
        mylog.debug(method=inspect.stack()[0][3], lineno=sys._getframe().f_lineno,
                    exception=ex)
        raise RuntimeError('radio int_status error')

    if (show is True):
        s_name =  'int_status_rsp_s'
        p_s = eval(s_name)
        p_d = p_s.build(p_g)
        mylog.debug('const config strings',method=inspect.stack()[0][3],
                    lineno=sys._getframe().f_lineno,
                    name=s_name, data=hexlify(p_d))
        mylog.debug('config structure',method=inspect.stack()[0][3],
                    lineno=sys._getframe().f_lineno,
                    data=radio_display_structs[p_s](p_s, p_d))
    if get_cmd_args().verbosity > 4:
        mylog.debug(method=inspect.stack()[0][3], lineno=sys._getframe().f_lineno,
                    results=p_g)
    return p_g


def show_int_rsp(radio, pend_flags):
    s_name =  'int_status_rsp_s'
    p_s = eval(s_name)
    clr_flags = clr_no_flags
    clr_flags.ph_pend.STATE_CHANGE = False
    p_g = radio.get_clear_interrupts(clr_flags)
    p_d = p_s.build(p_g)
    if get_cmd_args().verbosity > 1:
        mylog.debug(method=inspect.stack()[0][3],
                    lineno=sys._getframe().f_lineno,
                    name=s_name, data=hexlify(p_d))
        mylog.debug('interrupt structure',method=inspect.stack()[0][3],
                    lineno=sys._getframe().f_lineno,
                    data=radio_display_structs[p_s](p_s, p_d))


def msg_chunk_generator(radio, msg):
    index = 0
    while True:
        status = []
        __, tx_len = radio.fifo_info()
        tranche = index
        if (tx_len > 0):
            tranche = len(msg[index:]) if (len(msg[index:]) < tx_len) else tx_len
        yield msg[index:index+tranche], ['c',str(tx_len),str(tranche)]
        index += tranche

def collect_int_status(status):
    p = []
    for pend in [status.chip_pend, status.modem_pend, status.ph_pend]:
        for item in pend.iteritems():
            if item[1]:
                p.append(item[0])
    if get_cmd_args().verbosity > 4:
        mylog.debug('*** collect_int_status', method=inspect.stack()[0][3], lineno=sys._getframe().f_lineno,
                    status=status, progress=p)
    return p

def radio_send_msg(radio, msg, pwr=None):
    msg_chunk = msg_chunk_generator(radio, msg)
    start = time()
    progress = [start]
    bps       = get_ids_wds()['bps'] # radio speed in bits per second
    bits2send = len(msg) * 8 * 3     # time in bits to wait (3x msgs)
    bits2send += 64 * 8              # include long preamble
    time2wait = (1.0/bps) * bits2send * 1000
    time2wait *= 3                   # increase for good measure
    if get_cmd_args().verbosity > 3:
        mylog.debug(method=inspect.stack()[0][3], lineno=sys._getframe().f_lineno,
                    start=start, speed=bps,
                    bits=bits2send, delay=time2wait)

    if pwr:
        radio.set_power(pwr)
        progress.extend([time(),['Pwr',pwr]])

    # clear interrupts and report any pending
    ints = int_status(radio, clr_all_flags)
    if get_cmd_args().verbosity > 5:
        mylog.debug('*** radio_send_msg', method=inspect.stack()[0][3], lineno=sys._getframe().f_lineno,
                    int_status=ints)
    progress.extend(collect_int_status(ints))

    __, tx = radio.fifo_info(rx_flush=True, tx_flush=True)
    if (tx != MAX_FIFO_SIZE):
        progress.extend([time(), ['T', tx]])
        return progress

    chunk, p = msg_chunk.next()
    radio.write_tx_fifo(chunk)
    radio.start_tx(len(msg))
    progress.extend([time(), p])

    end  = time() + time2wait
    cflags = clr_no_flags
    now = time()
    while (now < end):
        status = int_status(radio, cflags)
        cflags = clr_no_flags
        no_action = True
        if (status.chip_pend.CMD_ERROR):
            cflags.chip_pend.CMD_ERROR = False
            no_action = False
            progress.extend([time(), 'E'])
            radio.fifo_info(rx_flush=True, tx_flush=True)
            mylog.error('cmd error',method=inspect.stack()[0][3],
                       data=collect_int_status(status))
        if (status.chip_pend.FIFO_UNDERFLOW_OVERFLOW_ERROR):
            cflags.chip_pend.FIFO_UNDERFLOW_OVERFLOW_ERROR = False
            no_action = False
            progress.extend([time(), ['U', collect_int_status(status)]])
            break
        if (status.ph_pend.TX_FIFO_ALMOST_EMPTY):
            cflags.ph_pend.TX_FIFO_ALMOST_EMPTY = False
            no_action = False
            chunk, p = next(msg_chunk)
            if (len(chunk)):
                radio.write_tx_fifo(chunk)
            progress.extend([time(), p])
        if (status.ph_pend.PACKET_SENT):
            cflags.ph_pend.PACKET_SENT = False
            no_action = False
            _, tx = radio.fifo_info()
            progress.extend([time(), ['f', tx]])
            break
        if (no_action):
            if (not progress):
                progress.extend([time(), 'p'])
            elif progress[-1] == 'p':
                progress.append(2)
            elif (isinstance(progress[-1], (int, long))) and (progress[-2] == 'p'):
                progress[-1] += 1
            else:
                progress.extend([time(), 'p'])
        now = time()
    if (now >= end):
        mylog.error('timeout', method=inspect.stack()[0][3])
        if get_cmd_args().verbosity > 3:
            mylog.debug(method=inspect.stack()[0][3], lineno=sys._getframe().f_lineno,
                        data=progress)
    __, tx = radio.fifo_info()
    progress.extend([time(), [':', len(msg), tx]])
    if get_cmd_args().verbosity > 3:
        mylog.debug('*** radio_send_msg', method=inspect.stack()[0][3], lineno=sys._getframe().f_lineno,
                    progress=progress)
    return progress


# Receive a complete message

def drain_rx_fifo(radio, p):
    rx_len, __ = radio.fifo_info()
    p.extend([time(), ['r', rx_len]])
    if (rx_len > MAX_FIFO_SIZE):
        rx_len = MAX_FIFO_SIZE
    # zzz rx = 0  # force the fifo read to fail to verify overrun error
    if (rx_len): return bytearray(radio.read_rx_fifo(rx_len))
    else:    return ''

def radio_receive_msg(radio, max_recv, wait):
    start = time()
    end = start + wait
    progress = [start]
    crc_err = False

    msg = bytearray()
    rssi = -1
    int_status(radio, clr_all_flags) # clear all interrupt pending flags
    radio.fifo_info(rx_flush=True, tx_flush=True)
    radio.start_rx(0)
    status = int_status(radio, clr_no_flags)
    while (time() < end):
        cflags = clr_no_flags
        no_action = True
        if (status.ph_pend.CRC_ERROR):
            cflags.ph_pend.CRC_ERROR = False     # clear
            no_action = False
            progress.extend([time(), 'C'])
            radio.fifo_info(rx_flush=True, tx_flush=True)
            crc_err = True
        if (status.chip_pend.CMD_ERROR):
            cflags.chip_pend.CMD_ERROR = False   # clear
            no_action = False
            status = radio.get_chip_status()
            progress.extend([time(), ['E', status.ph_pend, status.modem_pend, status.chip_pend]])
            radio.fifo_info(rx_flush=True, tx_flush=True)
            mylog.error('cmd error',method=inspect.stack()[0][3],
                       data=collect_int_status(status))
            #status = int_status(radio, clr_all_flags)
            #break
        if (status.modem_pend.INVALID_PREAMBLE):
            cflags.modem_pend.INVALID_PREAMBLE = False # clear
            no_action = False
            if (not progress):
                progress.extend([time(), 'p'])
            elif progress[-1] == 'p':
                progress.append(2)
            elif (isinstance(progress[-1], (int, long))) and (progress[-2] == 'p'):
                progress[-1] += 1
            else:
                progress.append('p')
        if (status.modem_pend.INVALID_SYNC):
            cflags.modem_pend.INVALID_SYNC = False  # clear
            no_action = False
            progress.extend([time(), 'S'])
        if (status.ph_pend.RX_FIFO_ALMOST_FULL):
            cflags.ph_pend.RX_FIFO_ALMOST_FULL = False  # clear
            no_action = False
            progress.extend([time(), 'a'])
            msg += drain_rx_fifo(radio, progress)
        if (status.ph_pend.PACKET_RX):
            no_action = False
            rssi = radio.fast_latched_rssi()
            cflags.ph_pend.PACKET_RX = False     # clear
            progress.extend([time(), 'f'])
            msg += drain_rx_fifo(radio, progress)
            progress.extend([time(), len(msg), rssi])
            break
        if (status.chip_pend.FIFO_UNDERFLOW_OVERFLOW_ERROR):
            cflags.chip_pend.FIFO_UNDERFLOW_OVERFLOW_ERROR = False  # clear
            no_action = False
            progress.extend([time(), 'O'])
            break
        status = int_status(radio, cflags)

    status = int_status(radio, clr_all_flags)       # clear all outstanding
    pkt_len = radio.get_packet_info()
    if (time() > end):
        progress.extend([time(), ['to','e',status]])
        msg = None
    elif crc_err:
        progress.extend([time(), ['crc','e',status]])
        mylog.error('crc error',method=inspect.stack()[0][3])
        if get_cmd_args().verbosity > 3:
            mylog.debug(method=inspect.stack()[0][3], lineno=sys._getframe().f_lineno,
                        rssi=rssi, data=progress)
        msg = None
    elif ((pkt_len + 1) != len(msg)):
        mylog.info('length error',method=inspect.stack()[0][3],
                   expected=pkt_len+1, got=len(msg))
        progress.extend([time(), ['len',pkt_len+1,len(msg),'e',status]])
        if get_cmd_args().verbosity > 3:
            mylog.debug(method=inspect.stack()[0][3], lineno=sys._getframe().f_lineno,
                        rssi=rssi, data=progress)
        msg = None
    return (msg, rssi, progress)


def radio_poll(radio, window=1000, slots=16, power=None, wait=None):
    '''
    Sends time, slot_time, slot_count, node_id, node_name,
    then receives none or more responses from any tags within
    radio 'earshot'. The poll request specifies the number of
    slots and time length of a slots. Each tag will use a
    random number to pick a slot (or no slot) and then wait
    the specified time period to respond with its node_id,
    software version, and event pending counter. Slot_time
    is in milliseconds.
    '''
    found      = {}
    last_rssi  = 0
    req_obj    = TagPoll(slot_width=window, slot_count=slots)
    req_msg    = req_obj.build()
    bps        = get_ids_wds()['bps']
    wait_time  = wait if (wait) else (slots * ((1.0 * window) / bps)) * 1000
    start      = time()
    end        = start + wait_time + SHORT_DELAY
    if get_cmd_args().verbosity > 2:
        mylog.debug(method=inspect.stack()[0][3], lineno=sys._getframe().f_lineno,
                    start=start, end=end,
                    total=end-start, delay=wait_time,
                    slots=slots, window=window, speed=bps)
    rstatus    = ''
    sstatus    = radio_send_msg(radio, req_msg, power)
    if get_cmd_args().verbosity > 3:
        mylog.debug(method=inspect.stack()[0][3], lineno=sys._getframe().f_lineno)
#                    name=req_obj.name,)
#                    payload=req_obj.payload,)
#                    data=hexlify(req_msg))
    while (time() < end):
        rsp_msg, rssi, rstatus = radio_receive_msg(radio, MAX_RECV,
                                                   end - time())
        if rsp_msg:
            last_rssi = rssi
            if get_cmd_args().verbosity > 3:
                mylog.debug(method=inspect.stack()[0][3], lineno=sys._getframe().f_lineno,
                            data=hexlify(rsp_msg))
            try:
                rsp_obj = TagMessage(rsp_msg)
            except (TlvBadException, TlvListBadException):
                mylog.warn('bad response',method=inspect.stack()[0][3])
                continue
            try:
                found[hexlify(rsp_obj.payload[0].value())] = [rssi] + \
                    [rsp_obj.payload[i].value() for i in range(1,len(rsp_obj.payload))]
            except (TlvBadException, TlvListBadException):
                mylog.warn('bad parameters',method=inspect.stack()[0][3])
                if get_cmd_args().verbosity > 3:
                    mylog.debug(method=inspect.stack()[0][3], lineno=sys._getframe().f_lineno,
                                data=radio.trace.filter(count=-20))
    if get_cmd_args().verbosity > 2:
        mylog.debug(method=inspect.stack()[0][3], lineno=sys._getframe().f_lineno,
                    elapsed=time()-start,
                    data=found)
    return found


def radio_get_position(radio, node=None, name=None, power=None, wait=MAX_WAIT):
    gps_geo = None
    if not node:
        node = TagTlv(tlv_types.NODE_ID, -1)
    if not name:
        name = TagName([node,
                            TagTlv('tag'),
                            TagTlv('info'),
                            TagTlv('sens'),
                            TagTlv('gps'),
                            TagTlv('xyz')])
    xyz_struct = pystruct.Struct('<iii')
    get_gps_xyz = TagGet(name)
    if get_cmd_args().verbosity > 2:
        mylog.debug(method=inspect.stack()[0][3], lineno=sys._getframe().f_lineno,
                    name=get_gps_xyz.name)
    req_msg = get_gps_xyz.build()
    error, payload, msg_meta = msg_exchange(radio, req_obj)
    rssi, sstatus, rstatus = msg_meta
    if (error is tlv_errors.SUCCESS):
        if payload:
            gps_xyz = payload2values(payload,
                                    [tlv_types.GPS,
                                    ])[0]
            if get_cmd_args().verbosity > 2:
                mylog.debug(method=inspect.stack()[0][3], lineno=sys._getframe().f_lineno,
                            data={'x':gps_xyz[0],
                                  'y':gps_xyz[0],
                                  'z':gps_xyz[0],})
            lon, lat, elv = transform(ecef, wgs84, *gps_xyz)
            gps_geo = float(lat), float(lon), float(elv)
            if get_cmd_args().verbosity > 2:
                mylog.debug('home geolocation', method=inspect.stack()[0][3], lineno=sys._getframe().f_lineno,
                            data={'latitude':gps_geo[0],
                                  'longitude':gps_geo[1],
                                  'elevation':gps_geo[0],})
            return gps_xyz, gps_geo
        else:
            mylog.error('response error',method=inspect.stack()[0][3],
                       error=error)
    else:
        mylog.error('timeout',method=inspect.stack()[0][3])
    return None, None




def radio_get_rssi(radio, node=None, name=None, power=None, wait=MAX_WAIT):
    if not node:
        node = TagTlv(tlv_types.NODE_ID, -1)
    if not name:
        name = TagName([node,
                            TagTlv('tag'),
                            TagTlv('.test'),
                            TagTlv('rssi')])
    req_obj = TagGet(name)
    req_msg = req_obj.build()
    error, payload, msg_meta = msg_exchange(radio, req_obj)
    rssi, sstatus, rstatus = msg_meta
    if (error is tlv_errors.SUCCESS):
        if payload:
            if get_cmd_args().verbosity > 3:
                mylog.debug('*** radio_get_rssi', method=inspect.stack()[0][3], lineno=sys._getframe().f_lineno,
                            payload=payload)
            tag_rssi = payload2values(payload,
                                    [tlv_types.INTEGER,
                                    ])[0]
            return tag_rssi, rssi, sstatus, rstatus
        return None, rssi, sstatus, rstatus
    return None, None, sstatus, rstatus


def radio_get_power(radio, node=None, name=None, power=None, wait=MAX_WAIT):
    if not node:
        node = TagTlv(tlv_types.NODE_ID, -1)
    if not name:
        name = TagName([node,
                            TagTlv('tag'),
                            TagTlv('.test'),
                            TagTlv('tx_pwr')])
    # zzz print('*** radio_get_power',name)
    req_obj = TagGet(name)
    req_msg = req_obj.build()
    error, payload, msg_meta = msg_exchange(radio, req_obj)
    rssi, sstatus, rstatus = msg_meta
    if (error is tlv_errors.SUCCESS):
        if payload:
            # zzz print('*** radio_get_power',payload)
            tag_power = payload2values(payload,
                                    [tlv_types.INTEGER,
                                    ])[0]
            return tag_power, rssi, sstatus, rstatus
    return None, None, sstatus, rstatus


def radio_set_power(radio, tag_power, node=None, name=None, power=None, wait=MAX_WAIT):
    if not node:
        node = TagTlv(tlv_types.NODE_ID, -1)
    if not name:
        name = TagName([node,
                            TagTlv('tag'),
                            TagTlv('.test'),
                            TagTlv('tx_pwr'),])
    req_obj = TagPut(name,
                     pl=TagTlvList([TagTlv(tlv_types.INTEGER,
                                           tag_power)]))
    req_msg = req_obj.build()
    error, payload, msg_meta = msg_exchange(radio, req_obj)
    rssi, sstatus, rstatus = msg_meta
    if (error is tlv_errors.SUCCESS):
        if payload:
            return payload[0].value(), rssi, sstatus, rstatus
    return None, None, sstatus, rstatus


def radio_get_rtctime(radio, node=None, name=None, power=None, wait=MAX_WAIT):
    if not node:
        node = TagTlv(tlv_types.NODE_ID, -1)
    if not name:
        name = TagName([node,
                            TagTlv('tag'),
                            TagTlv('sys'),
                            TagTlv('rtc')])
    req_obj = TagGet(name)
    if get_cmd_args().verbosity > 3:
        mylog.debug('*** radio_get_rtctime', method=inspect.stack()[0][3], lineno=sys._getframe().f_lineno,
                    name=name)
    error, payload, msg_meta = msg_exchange(radio, req_obj)
    rssi, sstatus, rstatus = msg_meta
    if (error is tlv_errors.SUCCESS):
        if payload:
            tagtime = payload2values(payload,
                                    [tlv_types.UTC_TIME,
                                    ])[0]
            return  tagtime, rssi, sstatus, rstatus
    return None, None, sstatus, rstatus


def radio_set_rtctime(radio, utctime, node=None, name=None, power=None, wait=MAX_WAIT):
    if not node:
        node = TagTlv(tlv_types.NODE_ID, -1)
    if not name:
        name = TagName([node,
                        TagTlv('tag'),
                        TagTlv('sys'),
                        TagTlv('rtc'),])
    req_obj = TagPut(name,
                     pl=TagTlvList([TagTlv(tlv_types.UTC_TIME,
                                           utctime)]))
    req_msg = req_obj.build()
    error, payload, msg_meta = msg_exchange(radio, req_obj)
    rssi, sstatus, rstatus = msg_meta
    if (error is tlv_errors.SUCCESS):
        if payload:
            tagtime = payload2values(payload,
                                    [tlv_types.UTC_TIME,
                                    ])[0]
            return tagtime, rssi, sstatus, rstatus
    return None, None, sstatus, rstatus


#<node_id>   "tag"  "test"   "zero"   "byte"
def radio_read_test(radio, test_name, pos, num, node=None, name=None, power=None, wait=MAX_WAIT):
    if not node:
        node = TagTlv(tlv_types.NODE_ID, -1)
    if not name:
        name = TagName([node,
                            TagTlv('tag'),
                            TagTlv('.test'),
                            TagTlv(test_name),
                            TagTlv('byte'),
                            TagTlv(tlv_types.OFFSET, pos),
                            TagTlv(tlv_types.SIZE, num),])
    req_obj = TagGet(name)
    if get_cmd_args().verbosity > 2:
        mylog.debug(method=inspect.stack()[0][3], lineno=sys._getframe().f_lineno,
                    name=req_obj.name)
    req_msg = req_obj.build()
    radio_send_msg(radio, req_msg, power);
    rsp_msg, rssi, status = radio_receive_msg(radio, MAX_RECV, wait)
    if rsp_msg:
        rsp_obj = TagMessage(rsp_msg)
        if get_cmd_args().verbosity > 2:
            mylog.debug(method=inspect.stack()[0][3], lineno=sys._getframe().f_lineno,
                        error=rsp_obj.header.options.param.error_code,
                        data=rsp_obj.payload.__repr__())
        if rsp_obj.payload:
            error, offset, amt, block = payload2values(rsp_obj.payload,
                                  [tlv_types.ERROR,
                                   tlv_types.OFFSET,
                                   tlv_types.SIZE,
                                   tlv_types.BLOCK,
                                  ])
            seta = set(block)
            if (len(seta) > 1):
                mylog.error('check error',  method=inspect.stack()[0][3],
                           diff=seta, size=amt,)
                amt = 0
            return error, offset, amt, block
        else:
            mylog.error('timeout', method=inspect.stack()[0][3],
                       error=rsp_obj.header.options.param.error_code)
    else:
        mylog.error('timeout', method=inspect.stack()[0][3],)
    return None


def radio_write_test(radio, test_name, buf, pos=0, node=None, name=None, power=None, wait=MAX_WAIT):
    if not node:
        node = TagTlv(tlv_types.NODE_ID, -1)
    if not name:
        name = TagName([node,
                        TagTlv('tag'),
                        TagTlv('.test'),
                        TagTlv(test_name),
                        TagTlv('byte'),
                        TagTlv(tlv_types.OFFSET, pos),
                        TagTlv(tlv_types.SIZE, len(buf)),])
    req_obj = TagPut(name, pl=buf)
    if get_cmd_args().verbosity > 2:
        mylog.debug(method=inspect.stack()[0][3], lineno=sys._getframe().f_lineno,
                    name=req_obj.name,
                    data=req_obj.payload.__repr__())
    req_msg = req_obj.build()
    sstatus = radio_send_msg(radio, req_msg, power)
    rsp_msg, rssi, rstatus = radio_receive_msg(radio, MAX_RECV, wait)
    if rsp_msg:
        if get_cmd_args().verbosity > 3:
            mylog.debug(method=inspect.stack()[0][3], lineno=sys._getframe().f_lineno,
                        data=rsp_msg.__repr__())
        rsp_obj = TagMessage(rsp_msg)
        if get_cmd_args().verbosity > 4:
            mylog.debug(method=inspect.stack()[0][3], lineno=sys._getframe().f_lineno,
                        data={'header':rsp_obj.header,
                              'name':rsp_obj.name,
                              'payload':rsp_obj.payload})
        if rsp_obj.payload:
            if get_cmd_args().verbosity > 3:
                mylog.debug(method=inspect.stack()[0][3], lineno=sys._getframe().f_lineno,
                            data=rsp_obj.payload.__repr__())
            error, offset = payload2values(rsp_obj.payload,
                                           [tlv_types.ERROR,
                                            tlv_types.OFFSET,
                                           ])
            if error and error != tlv_errors.SUCCESS:
                return error, offset
        return tlv_errors.SUCCESS, pos+len(buf)
    return tlv_errors.EINVAL, pos


# # UNIT TEST

def insert_space(st):
    p_ds = ''
    ix = 4
    i = 0
    p_s = hexlify(st)
    while (i < (len(st) * 2)):
        p_ds += p_s[i:i+ix] + ' '
        i += ix
    return p_ds


if (UNIT_TESTING):
    print('si446x driver version: {}\n'.format(radio_version()))
    radio = radio_start_radio()
    config = radio_config_radio(radio)
    print('compiled config strings (wdds + local):\n')
    for s in config:
        print('{}'.format(insert_space(s)))


if (UNIT_TESTING):
    info = radio.read_silicon_info()
    for s in info:
        print(insert_space(s[0]), s[1])
    print(radio.get_gpio())


if (UNIT_TESTING):
    response = []
    request = read_cmd_s.parse('\x00' * read_cmd_s.sizeof())
    request.cmd='PART_INFO'
    cmd = read_cmd_s.build(request)
    radio.spi.command(cmd, read_cmd_s.name)
    rsp = radio.spi.response(read_part_info_rsp_s.sizeof(),
                            read_part_info_rsp_s.name)
    if (rsp):
        response.append((rsp, read_part_info_rsp_s.parse(rsp)))
    request.cmd='FUNC_INFO'
    cmd = read_cmd_s.build(request)
    radio.spi.command(cmd, read_cmd_s.name)
    rsp = radio.spi.response(read_func_info_rsp_s.sizeof(),
                            read_func_info_rsp_s.name)
    if (rsp):
        response.append((rsp,read_func_info_rsp_s.parse(rsp)))
    print(response)


if (UNIT_TESTING):
    radio_show_config(radio.dump_radio())


if (UNIT_TESTING):
    for p_n in ['FRR_CTL', 'PA']:
        p_id = radio_config_group_ids.build(p_n)
        p_g = radio_config_groups[p_id]
        p_da = radio_get_group(radio, p_n)
        p_di = p_g.build(p_da)
        print('{} {}[{}]: ({}) {}'.format(p_n, p_g, hexlify(p_id), p_g.sizeof(), insert_space(p_di)))
        print(radio_display_structs[p_g](p_g, p_di))
        print(p_da)
        print()


if (UNIT_TESTING):
    s_name = 'pa_group_s'
    my_struct = eval(s_name)
    st = my_struct.parse('\x00' * my_struct.sizeof())
    data = my_struct.build(st)
    print('{}: {}'.format(s_name, radio_display_structs[my_struct](my_struct, data)))


if (UNIT_TESTING):
    pa_g = radio_get_group(radio, 'PA')
    pa_s = radio_config_groups[radio_config_group_ids.build('PA')]
    ps = pa_s.build(pa_g)
    print('{}: {}'.format(pa_s, insert_space(ps)))
    print(pa_g)
    print(radio_display_structs[pa_s](pa_s, ps))


if (UNIT_TESTING):
    print('\n programmed config strings:')
    for s in config:
        print(insert_space(s))
    print('\n const config strings:')
    for t in radio_get_raw_config():
        print(insert_space(t))
    assert(s==t)


if (UNIT_TESTING):
    g_name='FRR_CTL'
    g = radio_get_group(radio, g_name)
    print('{}: {}'.format(radio_config_groups[radio_config_group_ids.build(g_name)],
                          insert_space(radio_config_groups[radio_config_group_ids.build(g_name)].build(g))))
    print(g)


if (UNIT_TESTING):
    radio.set_power(10)
    g_name = 'PA'
    g = radio_get_group(radio, g_name)
    p = radio_config_groups[radio_config_group_ids.build(g_name)].build(g)
    print(radio_format_group('PA', p))
    radio.set_power(32)
    g = radio_get_group(radio, g_name)
    p = radio_config_groups[radio_config_group_ids.build(g_name)].build(g)
    print(radio_format_group('PA', p))


if (UNIT_TESTING):
    print(radio_get_group(radio, 'PA'))

if (UNIT_TESTING):
    """
    note that errors occur above threshold of 40. This implies interrupt latency is not satisfied.
    In runtime environment, use a value in range of 10 to 30. 10 could potentially cause more
    interrupts, but tolerates longer latency.
    """
    step = 1
    bb = bytearray(256)
    for i in range(len(bb)):
        bb[i] = i
    radio.trace._enable()
    ss = bytearray('\x10\x10')
    for thresh in range(20,21,step):
        print('thresh: {}'.format(thresh))
        ss[0] = thresh
        ss[1] = thresh
        radio.set_property('PKT', 0x0b, ss) # tx/rx threshold
        for i in range(80,81,step):
            bb[0] = i + 20
            pl = radio_send_msg(radio, bb[:i], 6)
            print('{} {}'.format(i, ''.join(map(str, pl))))
            print(hexlify(bb[:i]))
            if (pl[-1] == 'e'):
                print('ERROR {} {}'.format(i, ''.join(map(str, pl))))
            sleep(1)
    print('\ndone')

mylog.debug('initiialization complete')
