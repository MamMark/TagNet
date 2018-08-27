#!/usr/bin/env python
from __future__ import print_function, absolute_import, division
#from builtins import *                  # python3 types

__all__ = ['FileHandler',
           'TestBaseHandler',
           'TestEchoHandler',
           'TestOnesHandler',
           'TestZerosHandler',
           'TestSumHandler',
           'ByteIOFileHandler',
           'RtcFileHandler',
           'SparseIOFileHandler',
           'ImageIOFileHandler',
           'SimpleRecHandler',
           'DirHandler',
           'RootDirHandler',
           'PollNetDirHandler',
           'ImageDirHandler',
           'SysActiveDirHandler',
           'SysBackupDirHandler',
           'SysGoldenDirHandler',
           'SysNibDirHandler',
           'SysRunningDirHandler',
           'VerbosityDirHandler',
]

import os
import sys
import inspect
import logging
import structlog

###############################

from   sets          import Set
from   collections   import defaultdict, OrderedDict
from   errno         import ENOENT, ENODATA, EEXIST, EPERM, EINVAL, EIO
from   stat          import S_IFDIR, S_IFLNK, S_IFREG
from   time          import time
from   sets          import Set
from   fuse          import FuseOSError
from   binascii      import hexlify
from   datetime      import datetime

# If we are running from the source directory, try
# to load the module from there first.
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#print('{} init: argv:{}, basedir:{}'.format(os.path.basename(basedir),
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
    # zzz print('\n'.join(sys.path))

try:
    from radiofile   import file_get_bytes, file_put_bytes, file_update_attrs
    from radioimage  import im_put_file, im_get_file, im_delete_file, im_close_file
    from radioimage  import im_get_dir, im_set_version
    from radioutils  import path2list, radio_poll, radio_get_rtctime, radio_set_rtctime
    from tagfuseargs import get_cmd_args, set_verbosity, taglog, rootlog
    from sparsefile  import SparseFile
except ImportError:
    from tagfuse.radiofile   import file_get_bytes, file_put_bytes, file_update_attrs
    from tagfuse.radioimage  import im_put_file, im_get_file, im_delete_file, im_close_file
    from tagfuse.radioimage  import im_get_dir, im_set_version
    from tagfuse.radioutils  import path2list, radio_poll, radio_get_rtctime, radio_set_rtctime
    from tagfuse.tagfuseargs import get_cmd_args, set_verbosity, taglog, rootlog
    from tagfuse.sparsefile  import SparseFile

from tagnet              import tlv_errors, TagTlv

# new_inode            return next monotonically increasing number
#
base_value = 0
def new_inode():
    global base_value
    base_value += 1
    return base_value

# default_file_attrs   return default file attributes dict
#
def default_file_attrs(ntype, mode, nlinks, size):
        return dict(st_mode=(ntype | mode),
                    st_nlink=nlinks,
                    st_uid=os.getuid(),
                    st_gid=os.getgid(),
                    st_blksize=512,
                    st_size=size,
                    st_ctime=time(),
                    st_mtime=-1,
                    st_atime=-1)


class FileHandler(OrderedDict):
    '''
    Base File Handler class

    Performs all FUSE file related  operations.
    '''
    def __init__(self, ntype, mode, nlinks):
        a_dict = default_file_attrs(ntype,
                                    mode,
                                    nlinks,
                                    0)
        super(FileHandler, self).__init__(a_dict)
        self.inode = new_inode();
        self.log = structlog.getLogger('fuse.log-mixin.tagfuse.' + __name__).bind(
                scope=self.__class__.__name__)
        if get_cmd_args().verbosity > 4:
            self.log.debug('initialized',
                           method=inspect.stack()[0][3],
                           ntype=ntype,
                           mode=mode,
                           nlinks=nlinks,
                           inode=self.inode,
                           name=self.__class__.__name__)

    def __len__(self):
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3],
                           size=1)
        return 1

    def getattr(self, path_list, update=False):
        self['st_atime'] = time()  # set access time
        if get_cmd_args().verbosity > 1:
            self.log.debug(method=inspect.stack()[0][3],
                           atime=self['st_atime'],
                           update=update,
                           path_list=path_list,)
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3],
                           attrs=self.__repr__(),
                           path_list=path_list,)
        return self

    def flush(self, path_list):
        if get_cmd_args().verbosity > 1:
            self.log.debug(method=inspect.stack()[0][3],
                           path_list=path_list)
        return 0

    def link(self, link_name, target): # hard link
        self.log.warn('not implmented', method=inspect.stack()[0][3],
                       path_list=path_list)
        raise FuseOSError(EPERM)

    def read(self, path_list, size, offset):
        raise FuseOSError(ENODATA)

    def release(self, path_list):      # close
        if get_cmd_args().verbosity > 1:
            self.log.debug(method=inspect.stack()[0][3],
                           path_list=path_list)
        return 0

    def truncate(self, path_list, length):
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3],
                           path_list=path_list)
        return 0

    def unlink(self, path_list):       # delete
        self.log.warn('not implmented', method=inspect.stack()[0][3],
                       path_list=path_list)
        return 0
        # parent directory does the deleting

    def utimens(self, path_list, times):
        atime, mtime = times
        if get_cmd_args().verbosity > 1:
            self.log.debug(method=inspect.stack()[0][3],
                           times={'access':atime, 'modified':mtime},
                           path_list=path_list, )
        return 0

    def write(self, path_list, buf, offset):
        self.log.warn('not implmented', method=inspect.stack()[0][3],
                       path_list=path_list, offset=offset)
        raise FuseOSError(EPERM)


class ByteIOFileHandler(FileHandler):
    '''
    Byte IO File Handler class

    Performs Byte IO file specific operations.
    '''
    def __init__(self, radio, ntype, mode, nlinks):
        super(ByteIOFileHandler, self).__init__(ntype, mode, nlinks)
        self.radio = radio

    def getattr(self, path_list, update=False):
        if (update):
            file_update_attrs(self.radio, path_list, self)
        return super(ByteIOFileHandler, self).getattr(path_list, update=update)


    def read(self, path_list, size, offset):
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3],
                           size=size,
                           offset=offset,
                           path_list=path_list, )
        buf, eof = file_get_bytes(self.radio,
                                  path_list,
                                  size,
                                  offset)
        if get_cmd_args().verbosity > 1:
            self.log.debug(method=inspect.stack()[0][3],
                           size=len(buf),
                           eof=eof,
                           path_list=path_list, )
        return buf

    def write(self, path_list, buf, offset):
        if get_cmd_args().verbosity > 1:
            self.log.debug(method=inspect.stack()[0][3],
                           size=size,
                           offset=offset,
                           path_list=path_list, )
        return file_put_bytes(self.radio,
                        path_list,
                        buf,
                        offset)


class XyzFileHandler(FileHandler):
    '''
    Tagnet GPS/XYZ Tlv Type Handler class

    Performs operations on Tag's GPS XYZ position sensor.
    '''
    def __init__(self, radio, ntype, mode, nlinks):
        super(XyzFileHandler, self).__init__(ntype, mode, nlinks)
        self.radio = radio

    def getattr(self, path_list, update=False):
        return super(XyzFileHandler, self).getattr(path_list, update=update)

    def read(self, path_list, size, offset):
        if offset == 0:
            return ''
        xyz, geo = radio_get_position(self.radio,
                                 node=TagTlv(str(path_list[0])))
        if get_cmd_args().verbosity > 1:
            self.log.debug(method=inspect.stack()[0][3],
                           xyz=xyz,
                           geo=geo, )
        return xyz.__repr__()

class RtcFileHandler(FileHandler):
    '''
    Tagnet RTC Tlv Type Handler class

    Performs operations on Tag's real time clock. Can get current value
    as well as set it using either utimens (touch) or echo '0' > rtc
    '''
    def __init__(self, radio, ntype, mode, nlinks):
        super(RtcFileHandler, self).__init__(ntype, mode, nlinks)
        self.radio = radio

    def getattr(self, path_list, update=False):
        if update:
            epoch = datetime.utcfromtimestamp(0)
            utctime, a, b, c = radio_get_rtctime(self.radio,
                                    node=TagTlv(str(path_list[0])))
            if get_cmd_args().verbosity > 2:
                self.log.debug(method=inspect.stack()[0][3],
                               utctime=utctime, )
            try:
                self['st_mtime'] = (utctime - epoch).total_seconds()
            except TypeError:
                self['st_mtime'] = -2
            if get_cmd_args().verbosity > 1:
                self.log.debug(method=inspect.stack()[0][3],
                              utctime=utctime,
                              modified=self['st_mtime'], )
        return super(RtcFileHandler, self).getattr(path_list, update=update)

    def write(self, path_list, buf, offset):
        if offset:
            raise AttributeError
        radio_set_rtctime(self.radio,
                          datetime.utcnow(),
                          node=TagTlv(str(path_list[0])))
        return len(buf)

    def utimens(self, path_list, times):
        '''
        set tag rtctime to mtime (modified time) and
        update the local atime and mtime attributes.
        '''
        atime, mtime = times
        if get_cmd_args().verbosity > 1:
            self.log.debug(method=inspect.stack()[0][3],
                           times={'access':atime, 'modified':mtime}, )
        utctime = datetime.utcfromtimestamp(mtime)
        radio_set_rtctime(self.radio,
                          utctime,
                          node=TagTlv(str(path_list[0])))
        self['st_atime'] = atime
        self['st_mtime'] = mtime
        self.log.info(method=inspect.stack()[0][3],
                           utctime=utctime, )


class SparseIOFileHandler(ByteIOFileHandler):
    '''
    '''
    def __init__(self, *args, **kwargs):
        super(SparseIOFileHandler, self).__init__(*args, **kwargs)
        self.sparse = None
        self.path = None

    def _open_sparse(self, fpath):
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3],
                           sparse=self.sparse, disable=get_cmd_args().disable_sparse,
                           sparse_dir=get_cmd_args().sparse_dir, )
        if self.sparse is not None or get_cmd_args().disable_sparse:
            if get_cmd_args().verbosity > 2:
                self.log.debug('early exit', method=inspect.stack()[0][3], )
            return
        sparse_filename = os.path.join(
            get_cmd_args().sparse_dir,
            '_'.join(fpath))
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3],
                           file=sparse_filename,
                           sparse=self.sparse, )
        self.path = sparse_filename
        try:
            self.sparse = SparseFile(sparse_filename, get_cmd_args)
            self.log.info(method=inspect.stack()[0][3],
                           path=sparse_filename, )
        except:
            self.log.info('failed', method=inspect.stack()[0][3],
                          path=sparse_filename)
            raise
        items = sorted(self.sparse.items())
        if items:
            offset, block = items[-1]
            if self['st_size'] < (offset + len(block)):
                self['st_size'] = offset + len(block)
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3],
                           count=len(items), sparse=self.sparse)

    def _get_sparse(self, offset, size):
        if self.sparse is None or get_cmd_args().disable_sparse_read:
            return []
        return self.sparse.get_bytes_and_holes(offset, size)

    def _add_sparse(self, offset, buf):
        if self.sparse is not None:
            if get_cmd_args().verbosity > 2:
                self.log.debug(method=inspect.stack()[0][3],
                               offset=offset, size=len(buf))
            return self.sparse.add_bytes(offset, buf)
        return len(buf) # acknowledge but ignore data

    def _close_sparse(self):
        if self.sparse is not None:
            if get_cmd_args().verbosity > 2:
                self.log.debug(method=inspect.stack()[0][3],
                               path=self.path)
            self.sparse.flush()

    def _delete_sparse(self):
        if self.sparse is not None:
            self.sparse.clear()
            self.sparse.flush()
            self.sparse.drop()
            self.sparse = None
            self['st_size'] = 0
            self.log.info('deleted', method=inspect.stack()[0][3],
                          path=self.path)

    def flush(self, *args, **kwargs):
        self.log.info(method=inspect.stack()[0][3],
                      args=args[0],
                      path=self.path)
        self._close_sparse()
        super(SparseIOFileHandler, self).flush(*args, **kwargs)
        return 0

    def getattr(self, path_list, update=False):
        self.path = path_list
        self._open_sparse(path_list)
        return super(SparseIOFileHandler, self).getattr(path_list, update=update)

    def read(self, path_list, size, offset):
        if get_cmd_args().verbosity > 1:
            self.log.debug(method=inspect.stack()[0][3],
                           offset=offset,
                           size=size,
                           old_size=self['st_size'])
        # refresh the file size if seeking beyond our current size
        if offset >= self['st_size']:
            super(SparseIOFileHandler, self).getattr(path_list, update=True)
        if offset >= self['st_size']:
            raise FuseOSError(ENODATA)
        try:
            self._open_sparse(path_list)
        except:
            raise
        retbuf = bytearray()
        size = min(size, self['st_size'] - offset)
        work_list = self._get_sparse(offset, size)
        if (work_list):
            for item in work_list:
                if get_cmd_args().verbosity > 2:
                    self.log.debug(method=inspect.stack()[0][3],
                                   size=len(item),
                                   sample=hexlify(item[:20]))
                if isinstance(item, tuple) or \
                   isinstance(item, list):
                    first, last = item
                    last = min(last, self['st_size'])
                    xbuf, eof  = file_get_bytes(self.radio, path_list,
                                                last-first, first)
                    if (xbuf):
                        retbuf.extend(xbuf)
                        self._add_sparse(first, xbuf)
                    else:
                        break
                elif isinstance(item, bytearray) or \
                     isinstance(item, str):
                    retbuf.extend(item)
                else:
                    raise FuseOSError(EIO)
        elif offset < self['st_size']:
            if get_cmd_args().verbosity > 2:
                self.log.debug(method=inspect.stack()[0][3],
                               offset=offset,
                               size=self['st_size'])
            size = min(size, self['st_size']-offset)
            xbuf, eof  = file_get_bytes(self.radio, path_list,
                                        size, offset)
            if (xbuf):
                retbuf.extend(xbuf)
                self._add_sparse(offset, xbuf)
        if retbuf:
            if get_cmd_args().verbosity > 1:
                self.log.debug(method=inspect.stack()[0][3],
                               size=len(retbuf),
                               sample=hexlify(retbuf[:20]))
            return retbuf
        raise FuseOSError(ENODATA)

    def unlink(self, *args, **kwargs):       # delete
        self.log.info(method=inspect.stack()[0][3],
                      path=self.path,
                      sparse=self.sparse)
        self._delete_sparse()
        return 0

    def write(self, path_list, buf, offset):
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3],
                           offset=offset,
                           size=len(buf), )
        self._open_sparse(path_list)
        sz = self._add_sparse(offset, buf)
        if (offset + sz) > self['st_size']:
            self['st_size'] = offset + sz
        if get_cmd_args().verbosity > 1:
            self.log.debug(method=inspect.stack()[0][3],
                           offset=offset, size=sz, )
        return sz


class ImageIOFileHandler(ByteIOFileHandler):
    '''
    Image IO File Handler class

    Performs Image IO file specific operations.
    '''
    def __init__(self, radio, ntype, mode, nlinks):
        super(ImageIOFileHandler, self).__init__(radio, ntype, mode, nlinks)
        self.offset = 0

    def getattr(self, path_list, update=False):
        path_list[-1] = '<version:'+'.'.join(path_list[-1].split('.'))+'>'
        return super(ImageIOFileHandler, self).getattr(path_list, update=update)

    def flush(self, path_list): # close
        path_list[-1] = '<version:'+'.'.join(path_list[-1].split('.'))+'>'
        self['st_size'] = im_close_file(self.radio, path_list, self.offset)
        if get_cmd_args().verbosity > 1:
            self.log.debug(method=inspect.stack()[0][3],
                           path_list=path_list,
                           size=self['st_size'])
        return 0

    def read(self, path_list, size, offset):
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3],
                           offset=offset,
                           size=size,)
        error, buf, offset = im_get_file(self.radio,
                               path_list,
                               size,
                               offset)
        if get_cmd_args().verbosity > 1:
            self.log.debug(method=inspect.stack()[0][3],
                           eof=eof,
                           size=len(buf),
                           error=error)
        if (error) and (error is not tlv_errors.SUCCESS):
            raise FuseOSError(ENODATA)
        return str(buf)

    def release(self, path_list): # close
        self.log.info(method=inspect.stack()[0][3], path_list=path_list)
        return 0

    def unlink(self, path_list):  # delete
        version = '<version:'+'.'.join(path_list[-1].split('.'))+'>'
        new_path_list = path_list[:-1]
        new_path_list.append(version)
        self.log.info(method=inspect.stack()[0][3],
                      version=version, path_list=path_list)
        if im_delete_file(self.radio, new_path_list):
            return 0
        raise FuseOSError(ENOENT)

    def write(self, path_list, buf, offset):
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3],
                           offset=offset,
                           size=len(buf), )
        error, new_offset = im_put_file(self.radio,
                           path_list,
                           buf,
                           offset)
        if get_cmd_args().verbosity > 1:
            self.log.debug(method=inspect.stack()[0][3],
                           offset=new_offset, size=len(buf))
        if (error) and (error is not tlv_errors.SUCCESS):
            raise FuseOSError(ENOENT)
        if (new_offset):
            self.offset = new_offset
            return(new_offset - offset)
        else:
            return len(buf)


class SimpleRecHandler(FileHandler):
    '''Simple Record Handler class

    Performs Simple Record IO.

    A simple record is an object that is referenced by a record
    number rather by a byte offset.  The offset is the record number
    for what ever record we are talking about.

    If we want to write another record to the remote, we have to
    specific the next record number when we do the write.

    We use the file size (st_size) to remember how many records are in the
    object.  So if we want to write another record we have specify
    st_size + 1.

    This also has the nice property of showing up in an 'ls -l note'.  The
    'file size' of note is the last note number written.

    '''
    def __init__(self, radio, ntype, mode, nlinks):
        super(SimpleRecHandler, self).__init__(ntype, mode, nlinks)
        self.radio = radio

    def getattr(self, path_list, update=False):
        if (update):
            file_update_attrs(self.radio, path_list, self)
        return super(SimpleRecHandler, self).getattr(path_list, update=update)

    def write(self, path_list, buf, offset):
        last_seq = self['st_size']
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3],
                           path_list=path_list,
                           size=len(buf),
                           offset=offset,
                           sequence=last_seq)
        if (offset and offset != last_seq) or (len(buf) > 200):
            raise FuseOSError(EINVAL)
        self['st_size'] = file_put_bytes(self.radio,
                              path_list, buf, last_seq + 1)
        if get_cmd_args().verbosity > 1:
            self.log.debug(method=inspect.stack()[0][3],
                           size=self['st_size'],
                           sample=hexlify(buf[:20]),
                           path_list=path_list)
        return len(buf)


class SysFileHandler(FileHandler):
    '''
    System Executive File Handler class

    Performs file specific operations on System Executive Facts.
    This class is dynamically created by SysDirHandler when adding
    image version file names.
    '''
    def __init__(self, radio, ntype, mode, nlinks):
        super(SysFileHandler, self).__init__(ntype, mode, nlinks)
        self.radio = radio


class TestBaseHandler(FileHandler):
    '''
    '''
    def __init__(self, ntype, mode, nlinks):
        super(TestBaseHandler, self).__init__(ntype, mode, nlinks)
        self.buf   = ''
        self['st_size'] = 0
        self.sum   = 0

    def release(self, path_list):      # close
        self.buf   = ''
        self.sum   = 0
        return 0

class TestZerosHandler(TestBaseHandler):
    '''
    '''
    def __init__(self, ntype, mode, nlinks):
        super(TestZerosHandler, self).__init__(ntype, mode, nlinks)

    def read(self, path_list, size, offset):
        buf = chr(0) * size
        return buf

    def write(self, path_list, buf, offset):
        if (buf[0] == 0) and len(Set(buf)) == 1:
            self['st_size'] += len(buf)
            self.sum   += sum(map(ord,buf))
            dsize       = len(buf)
        else:
            raise FuseOSError(EIO)
        return dsize


class TestOnesHandler(TestBaseHandler):
    '''
    '''
    def __init__(self, ntype, mode, nlinks):
        super(TestOnesHandler, self).__init__(ntype, mode, nlinks)

    def read(self, path_list, size, offset):
        buf = chr(0xff) * size
        return (str(buf))

    def write(self, path_list, buf, offset):
        if (buf[0] == 0xff) and len(Set(buf)) == 1:
            self['st_size'] += len(buf)
            self.sum   += sum(map(ord,buf))
            dsize       = len(buf)
        else:
            raise FuseOSError(EIO)
        return dsize


class TestEchoHandler(TestBaseHandler):
    '''
    '''
    def __init__(self, *args, **kwargs):
        super(TestEchoHandler, self).__init__(*args, **kwargs)
        self.sparse = None

    def _open_sparse(self, fpath):
        if (self.sparse == None):
            self.sparse = SparseFile('_'.join(fpath), get_cmd_args)
            items = sorted(self.sparse.items())
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3], size=len(items))
            if items:
                offset, block = items[-1]
                self['st_size'] = offset + len(block)
            else:
                self['st_size'] = 0
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3], sparse=self.sparse)

    def _close_sparse(self):
        if self.sparse:
            self.sparse.flush()
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3], sparse=self.sparse)

    def _delete_sparse(self):
        if self.sparse:
            self.sparse.drop()
            self.sparse = None
            self['st_size'] = 0
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3], sparse=self.sparse)

    def flush(self, path_list):
        self.log.debug(method=inspect.stack()[0][3],
                       path_list=path_list, )
        self._close_sparse()
        return 0

    def getattr(self, path_list, update=False):
        self._open_sparse(path_list)
        return super(TestEchoHandler, self).getattr(path_list, update=update)

    def read(self, path_list, size, offset):
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3],
                           offset=offset,
                           size=size,
                           path_list=path_list, )
        if offset >= self['st_size']:
            raise FuseOSError(ENODATA)
        self._open_sparse(path_list)
        retbuf = bytearray()
        size = min(size, self['st_size'] - offset)
        work_list = self.sparse.get_bytes_and_holes(offset, size)
        if (work_list):
            for item in work_list:
                if isinstance(item, tuple) or \
                   isinstance(item, list):
                    if get_cmd_args().verbosity > 2:
                        self.log.debug(method=inspect.stack()[0][3], data=item)
                    first, last = item
                    last = min(last, self['st_size'])
                    xbuf = bytearray('\x00' * (last - first))
                    if (xbuf):
                        retbuf.extend(xbuf)
                    else:
                        break
                elif isinstance(item, bytearray) or \
                     isinstance(item, str):
                    if get_cmd_args().verbosity > 2:
                        self.log.debug(method=inspect.stack()[0][3],
                                       size=len(item), data=hexlify(item[:24]))
                    retbuf.extend(item)
                else:
                    if get_cmd_args().verbosity > 2:
                        self.log.debug(method=inspect.stack()[0][3],
                                       error=EIO, data=item)
                    raise FuseOSError(EIO)
            return retbuf
        else:
            retbuf.extend(bytearray('\x00' * size))
            return retbuf
        raise FuseOSError(ENODATA)

    def unlink(self, path_list):       # delete
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3],
                           sparse=self.sparse,
                           path_list=path_list)
        self._delete_sparse()
        return 0

    def write(self, path_list, buf, offset):
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3],
                           offset=offset,
                           size=len(buf),)
        self._open_sparse(path_list)
        sz = self.sparse.add_bytes(offset, buf)
        if (offset + sz) > self['st_size']:
            self['st_size'] = offset + sz
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3],
                           size=sz,)
        return sz


class TestSumHandler(TestBaseHandler):
    '''
    '''
    def __init__(self, ntype, mode, nlinks):
        super(TestSumHandler, self).__init__(ntype, mode, nlinks)

    def getattr(self, path_list, update=False):
        self['st_size'] = self.sum
        return super(TestSumHandler, self).getattr(path_list, update=update)

    def read(self, path_list, size, offset):
        buf = 'S' * size
        return buf

    def write(self, path_list, buf, offset):
        if (offset == len(self.buf)):
            self['st_size'] += len(buf)
            self.sum   += sum(map(ord,buf))
            dsize       = len(buf)
        else:
            raise FuseOSError(EIO)
        return dsize


class DirHandler(OrderedDict):
    '''
    Base Directory Handler class

    Performs all FUSE directory related operations.
    '''
    def __init__(self, a_dict):
        super(DirHandler, self).__init__(a_dict)
        self.inode = new_inode()
        self.log = structlog.getLogger('fuse.log-mixin.tagfuse.' + __name__).bind(
                scope=self.__class__.__name__)
        if get_cmd_args().verbosity > 4:
            self.log.debug('initialized',
                           method=inspect.stack()[0][3],
                           name=self.__class__.__name__)
        self.parent = None

    def traverse(self, parent, path_list, index):
        """
        Traverse the directory tree until reaching the leaf identified
        by path_list.

        returns the handler for which the path_list refers as well
        as the modified path_list.
        The path_list may be modified post execution of the base
        class to handle any required conversion from printable
        filenames to Tagnet TLV types.
        Directory keys are printable filenames.
        """
        self.parent = parent
        if get_cmd_args().verbosity > 4:
            self.log.debug(method=inspect.stack()[0][3],
                           parent=type(parent), index=index, path_list=path_list)
        if index < (len(path_list) - 1):      # look in subdirectory
            for key, handler in self.iteritems():
                if (path_list[index] == key):
                    if isinstance(handler, DirHandler):
                        return handler.traverse(self, path_list, index + 1)
        else:
            for key, handler in self.iteritems():
                if get_cmd_args().verbosity > 4:
                    self.log.debug(method=inspect.stack()[0][3],
                                   name=key, handler=type(handler))
                # match the terminal name
                if (path_list[index] == key):
                    handler.parent = self
                    return (handler, path_list)
            self.log.warn('fail', method=inspect.stack()[0][3],
                      index=index, path_list=path_list)
        return (None, None)           # no match found

    def create(self, path_list, mode):
        self.log.warn('not implmented', method=inspect.stack()[0][3],
                       path_list=path_list)
        raise FuseOSError(EINVAL)

    def getattr(self, path_list, update=False):
        if get_cmd_args().verbosity > 1:
            self.log.debug(method=inspect.stack()[0][3],
                           path_list=path_list, update=update)
        return self['']

    def readdir(self, path_list, tree_root, new_tag_def):
        dir_names = ['.','..']
        for name in self.keys():
            if (name != ''):
                dir_names.append(name)
        if get_cmd_args().verbosity > 1:
            self.log.debug(method=inspect.stack()[0][3],
                           dir_list=dir_names,
                           path_list=path_list)
        self['']['st_nlink'] = len(dir_names)
        return dir_names

    def link(self, link_name, target):
        self.log.info(method=inspect.stack()[0][3],
                      link_name=link_name,
                      target=target)
        return 0

    def unlink(self, path_list):
        self.log.info(method=inspect.stack()[0][3],
                      path_list=path_list)
        return 0

    def utimens(self, path_list, times):
        atime, mtime = times
        if get_cmd_args().verbosity > 1:
            self.log.debug(method=inspect.stack()[0][3],
                           times={'access':atime, 'modified':mtime},
                           path_list=path_list, )
        return 0


class RootDirHandler(DirHandler):
    '''
    Tag Tree Root Directory Handler class
    '''
    def __init__(self, a_dict):
        super(RootDirHandler, self).__init__(a_dict)
        self.parent = None

    def traverse(self, parent, path_list, index):
        '''
        perform normal traverse operation followed by a fixup of
        the node_id string in the path_list. Want to convert
        from human readable to <k:v> format so that proper type
        is associated with this path element. When converting
        the path element, don't modify if element is the empty
        string (file attributes) or a dot file (special in this
        level).
        '''
        self.parent = parent
        handler, path_list = super(RootDirHandler, self).traverse(self, path_list, index)
        if path_list and path_list[index] is not '' and not path_list[index].startswith('.'):
            path_list[index] = '<node_id:' + path_list[index] + '>'
        if get_cmd_args().verbosity > 4:
            self.log.debug(method=inspect.stack()[0][3],
                           parent=type(parent), index=index, path_list=path_list)
        return (handler, path_list)


class PollNetDirHandler(DirHandler):
    '''
    Network Polling Directory Handler class

    Performs polling for new tags and adds them to root directory.
    '''
    def __init__(self, radio, count, active, a_dict):
        '''
        radio      instance of radio to use for I/O
        count      maximum number of iterations to poll
        active     name of directory with tags found by
                   previous poll
        '''
        super(PollNetDirHandler, self).__init__(a_dict)
        self.radio      = radio
        self.poll_count = count
        self.active    = active

    def readdir(self, path_list, tree_root, new_tag):
        '''
        look for any new tags in the neighborhood and add them
        to this node's children. A whole new instance of the
        tagtree is instantiated for each tag. Existing tags that
        are no longer reachable stay in the tree and must be
        explicitly deleted.
        radio_poll returns a 4-tuple of which we only are
        interested in the first item (not interested in rssi,
        tx status, rx status).
        The tag_list is a list of all tags that responded to the
        poll. Each item in the list is a tuple of info about that
        tag. The first item is its node id, which we use for the
        directory entry name.
        '''
        if get_cmd_args().verbosity > 2:
            self.log.info(method=inspect.stack()[0][3],
                          parent=type(self.parent),
                          active=type(self.parent[self.active]),
                          me=type(self), )

        # clean directory of tags previously added to poll/new
        if self.parent[self.active] is not self:
            for tag in self.keys():
                if tag is '' or tag.startswith('.'):
                    continue
                del self[tag]

        # build list of known tags found in poll/active
        my_names = []
        for tag in self.parent[self.active].keys():
            if tag is '' or tag.startswith('.'):
                continue          # skip special files
            my_names.append(tag)
        my_set = Set(my_names)    # tags currently active

        # poll for list of new tags
        tag_set = Set()           # tags found by polling
        new_set = Set()           # tags added to new list
        more = 0
        for i in range(self.poll_count):
            tag_set |= Set(radio_poll(self.radio).keys())
            new_set |= tag_set.difference(my_set)
            if get_cmd_args().verbosity > 2:
                self.log.debug(method=inspect.stack()[0][3],
                              local=my_set,
                              new=new_set,
                              tag=tag_set)
            if new_set:
                if more > 3:      # keep looking for a few more
                    break
                more += 1
        if get_cmd_args().verbosity > 1:
            self.log.debug(method=inspect.stack()[0][3],
                           local=my_set,
                           new=new_set,
                           tag=tag_set)

        # add new found tags
        for tag in new_set:
            # Add new Tag tree onto root of TagFuse tree
            # and use passed function to instantiate it
            tree_root[tag] = new_tag(self.radio)
            # also add tag name to poll/active directory
            self.parent[self.active][tag] = FileHandler(S_IFREG, 0o444, 1)
            self.parent[self.active][tag]['st_mtime'] = time()
            tree_root['']['st_nlink'] += 1

        # update time for tags that responded previously
        for tag in my_set.difference(tag_set):
            self.parent[self.active][tag]['st_mtime'] = time()


        dir_names = ['.','..'] + list(new_set)
        if self.parent[self.active] == self:
            dir_names += list(my_set)

        self.log.info('poll results',
                      method=inspect.stack()[0][3],
                      dir_list=dir_names)
        return dir_names

    def create(self, path_list, mode):
        file_name = path_list[-1]
        self.log.info(method=inspect.stack()[0][3],
                      path_list=path_list[:-1],
                      mode=oct(mode),
                      file=file_name)
        # add if this instance is poll/active handler
        if self.parent[self.active] == self:
            try:
                x = self.parent[self.active][file_name]
                raise FuseOSError(EEXIST)
            except KeyError:
                self.parent[self.active][file_name] = FileHandler(S_IFREG, 0o444, 1)
                self.parent[self.active][file_name]['st_mtime'] = time()
        return 0

    def unlink(self, path_list):       # delete
        self.log.info(method=inspect.stack()[0][3],
                      path_list=path_list)
        # delete if this instance is the poll/active handler
        if self.parent[self.active] == self:
            del self[path_list[-1]]
        return 0


class ImageDirHandler(DirHandler):
    '''
    Software Images Directory Handler class

    Performs image directory specific operations.
    '''
    def __init__(self, radio, a_dict):
        super(ImageDirHandler, self).__init__(a_dict)
        self.radio = radio

    def readdir(self, path_list, tree_root, new_tag_def):
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3], path_list=path_list)
        tag_dir = im_get_dir(self.radio, path_list)
        if (tag_dir):
            # make set of versions found on tag
            tag_versions = []
            for version, state in tag_dir:
                self.log.debug(method=inspect.stack()[0][3],
                              version=version,
                              state=str(state))
                if (str(state) != 'x'):
                    tag_versions.append('.'.join(map(str, version)))
            tag_set = Set(tag_versions)
            # make set of version founds on self
            my_versions = []
            for version in self.keys():
                if version is not '':
                    my_versions.append(version)
            my_set = Set(my_versions)
            self.log.info(method=inspect.stack()[0][3],
                          local=my_set,
                          tag=tag_set)

            # add versions on tag but not on self
            for version in tag_set.difference(my_set):
                self[version] = ImageIOFileHandler(
                    self.radio,
                    S_IFREG,
                    0o664,
                    1)
            # remove versions on self but not on tag
            for version in my_set.difference(tag_set):
                try:
                    del self[version]
                except KeyError:
                    pass  # wasn't there, ok

        if get_cmd_args().verbosity > 1:
            self.log.debug(method=inspect.stack()[0][3], dir=self)
        return super(ImageDirHandler, self).readdir(path_list, tree_root, new_tag_def)

    def create(self, path_list, mode):
        file_name = path_list[-1]
        self.log.info(method=inspect.stack()[0][3],
                      path_list=path_list[:-1],
                      mode=oct(mode),
                      file=file_name)
        try:
            x = self[file_name]
            raise FuseOSError(EEXIST)
        except KeyError:
            self[file_name] = ImageIOFileHandler(self.radio,
                                                 S_IFREG,
                                                 0o664,
                                                 1)
        return 0

    def unlink(self, path_list):  # delete
        self.log.info(method=inspect.stack()[0][3], path_list=path_list)
        del self[path_list[-1]]   # last element is version
        return 0

    def release(self, path_list): # close
        self.log.info(method=inspect.stack()[0][3], path_list=path_list)
        return 0


class SysDirHandler(DirHandler):
    '''
    System Active Directory Handler class

    Performs active directory specific operations.
    '''
    def __init__(self, radio, a_dict):
        super(SysDirHandler, self).__init__(a_dict)
        self.radio = radio

    def readdir(self, path_list, tree_root, new_tag_def, img_state=''):
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3], path_list=path_list)
        tag_dir = im_get_dir(self.radio, path_list)
        if (tag_dir):
            # make set of versions found on tag
            tag_versions = []
            for version, state in tag_dir:
                if (img_state == '') or (img_state == state):
                    tag_versions.append('.'.join(map(str, version)))
            tag_set = Set(tag_versions)
            if get_cmd_args().verbosity > 2:
                self.log.debug(method=inspect.stack()[0][3], tag=tag_set)
            # make set of version founds on self
            my_versions = []
            for version in self.keys():
                if version is not '':
                    my_versions.append(version)
            my_set = Set(my_versions)
            if get_cmd_args().verbosity > 2:
                self.log.debug(method=inspect.stack()[0][3], tag=my_set)

            # add versions on tag but not on self
            for version in tag_set.difference(my_set):
                self[version] = ImageIOFileHandler(
                    self.radio,
                    S_IFREG,
                    0o664,
                    1)
            # remove versions on self but not on tag
            for version in my_set.difference(tag_set):
                del self[version]
        if get_cmd_args().verbosity > 1:
            self.log.debug(method=inspect.stack()[0][3], dir=self)
        return super(SysDirHandler, self).readdir(path_list, tree_root, new_tag_def)


class SysActiveDirHandler(SysDirHandler):
    '''
    System Active Directory Handler class

    Performs active directory specific operations.
    '''
    def __init__(self, radio, a_dict):
        super(SysActiveDirHandler, self).__init__(radio, a_dict)

    def link(self, ln_l, tg_l):
        if get_cmd_args().verbosity > 2:
            self.log.debug(method=inspect.stack()[0][3],
                           local_name=ln_l,
                           target=tg_l)
        # set new version on tag active directory
        new_version = tg_l[-1]
        ln_lv = ln_l
        ln_lv.append(new_version)
        err = im_set_version(self.radio, ln_lv)
        # if a timeout occurs, we assume success. may need to do better
        if (err == tlv_errors.SUCCESS) or (err == tlv_errors.ETIMEOUT):
            # remove existing link(s), if any
            for version, handler in self.iteritems():
                if version != '':
                    del self[version]
            # add new link
            self[new_version] = SysFileHandler(self.radio,
                                        S_IFREG,
                                        0o664,
                                        1)
            self.log.info(method=inspect.stack()[0][3],
                          version=new_version)
            return 0
        self.log.info('timeout', method=inspect.stack()[0][3],
                      version=new_version)
        return 0

    def readdir(self, path_list, tree_root, new_tag_def):
        dir = super(SysActiveDirHandler, self).readdir(
            path_list, tree_root, new_tag_def, img_state='active')
        self.log.info(method=inspect.stack()[0][3], dir=dir)
        return dir

    def unlink(self, path_list):
        self.log.info(method=inspect.stack()[0][3], path_list=path_list)
        return 0


class SysBackupDirHandler(SysDirHandler):
    '''
    System Backup Directory Handler class

    Performs backup directory specific operations.
    '''
    def __init__(self, radio, a_dict):
        super(SysBackupDirHandler, self).__init__(radio, a_dict)

    def link(self, ln_l, tg_l):
        self.log.debug(method=inspect.stack()[0][3], local_name=ln_l, target=tg_l)
        # set new version on tag backup directory
        new_version = tg_l[-1]
        ln_lv = ln_l
        ln_lv.append(new_version)
        err = im_set_version(self.radio, ln_lv)
        # if a timeout occurs, we assume success. may need to do better
        if (err == tlv_errors.SUCCESS) or (err == tlv_errors.ETIMEOUT):
            # remove existing link(s), if any
            for version, handler in self.iteritems():
                if version != '':
                    del self[version]
            # add new link
            self[new_version] = SysFileHandler(self.radio,
                                        S_IFREG,
                                        0o664,
                                        1)
            self.log.info(method=inspect.stack()[0][3],
                          version=new_version)
            return 0
        return 0

    def readdir(self, path_list, tree_root, new_tag_def):
        dir = super(SysBackupDirHandler, self).readdir(
                       path_list, tree_root, new_tag_def, img_state='backup')
        self.log.info(method=inspect.stack()[0][3], dir=dir)
        return dir

    def unlink(self, path_list):
        self.log.info(method=inspect.stack()[0][3], path_list=path_list)
        return 0


class SysGoldenDirHandler(SysDirHandler):
    '''
    System Golden Directory Handler class

    Performs Golden directory specific operations.
    '''
    def __init__(self, radio, a_dict):
        super(SysGoldenDirHandler, self).__init__(radio, a_dict)


class SysNibDirHandler(SysDirHandler):
    '''
    System NIB Directory Handler class

    Performs NIB directory specific operations.
    '''
    def __init__(self, radio, a_dict):
        super(SysNibDirHandler, self).__init__(radio, a_dict)


class SysRunningDirHandler(SysDirHandler):
    '''
    System Running Directory Handler class

    Performs running directory specific operations.
    '''
    def __init__(self, radio, a_dict):
        super(SysRunningDirHandler, self).__init__(radio, a_dict)


class VerbosityDirHandler(DirHandler):
    '''
    Debug Verbosity Directory Handler class

    Set and get verbosity level using file system.
    '''
    def __init__(self, a_dict):
        super(VerbosityDirHandler, self).__init__(a_dict)
        self.file_name = str(get_cmd_args().verbosity)
        self[self.file_name] = FileHandler(S_IFREG, 0o444, 1)

    def create(self, path_list, mode):
        '''
        delete current setting and replace with new value
        '''
        file_name = path_list[-1]
        set_verbosity(int(file_name))
        if get_cmd_args().verbosity > 4:
            self.log.debug(method=inspect.stack()[0][3],
                           file=file_name,
                           mode=oct(mode),
                           path_list=path_list)
        del self[self.file_name]
        self[file_name] = FileHandler(S_IFREG, 0o444, 1)
        self.file_name=file_name
        self.log.warn('set verbosity',
                      method=inspect.stack()[0][3],
                      verbosity=get_cmd_args().verbosity,
                      path_list=path_list)
        return 0

taglog.debug('initiialization complete')
