#!/usr/bin/env python3
'''
passthroughfs.py - Example file system for pyfuse3
This file system mirrors the contents of a specified directory tree.
Caveats:
 * Inode generation numbers are not passed through but set to zero.
 * Block size (st_blksize) and number of allocated blocks (st_blocks) are not
   passed through.
 * Performance for large directories is not good, because the directory
   is always read completely.
 * There may be a way to break-out of the directory tree.
 * The readdir implementation is not fully POSIX compliant. If a directory
   contains hardlinks and is modified during a readdir call, readdir()
   may return some of the hardlinked files twice or omit them completely.
 * If you delete or rename files in the underlying file system, the
   passthrough file system will get confused.
Copyright ©  Nikolaus Rath <Nikolaus.org>
Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''

import os
import sys
import shutil
import hashlib
from functools import partial
# If we are running from the pyfuse3 source directory, try
# to load the module from there first.
basedir = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), '..'))
if (os.path.exists(os.path.join(basedir, 'setup.py')) and
    os.path.exists(os.path.join(basedir, 'src', 'pyfuse3.pyx'))):
    sys.path.insert(0, os.path.join(basedir, 'src'))

import pyfuse3
from argparse import ArgumentParser
import errno
import logging
import stat as stat_m
from pyfuse3 import FUSEError
from os import fsencode, fsdecode
from collections import defaultdict
import trio


import faulthandler
faulthandler.enable()

log = logging.getLogger(__name__)
def getsha256(filename):
    """SHA256 used to verify the integrity of the encoded file"""
    with open(filename, mode='rb') as fin:
        d = hashlib.sha256()
        for buf in iter(partial(fin.read, 1024*1024), b''):
            d.update(buf)
    return d.digest()
#Checks integrity of any File  
def check_integrity(path_to_file):
    print("Checking integrity of ", path_to_file)
    if not os.path.exists(path_to_file):
        print(1, "sbx file '%s' not found" % (path_to_file))
        return
    fin = open(path_to_file, "rb", buffering=1024*1024)
    buffer = fin.read(512)
    header = fin.read(4)
    buffer = buffer[16:]
    if header[:3] != b"SBx":
        print(1, "not a SeqBox file!")
        return
    metadata = {}
    p=0
    while p < (len(buffer)-3):
        metaid = buffer[p:p+3]
        p+=3
        if metaid == b"\x1a\x1a\x1a":
            break
        else:
            metalen = buffer[p]
            metabb = buffer[p+1:p+1+metalen]
            p = p + 1 + metalen    
            if metaid == b'FNM':
                metadata["filename"] = metabb.decode('utf-8')
            if metaid == b'SNM':
                metadata["sbxname"] = metabb.decode('utf-8')
            if metaid == b'FSZ':
                metadata["filesize"] = int.from_bytes(metabb, byteorder='big')
            if metaid == b'FDT':
                metadata["filedatetime"] = int.from_bytes(metabb, byteorder='big')
            if metaid == b'SDT':
                metadata["sbxdatetime"] = int.from_bytes(metabb, byteorder='big')
            if metaid == b'HSH':
                metadata["hash"] = metabb
    if "hash" in metadata:
        hashtype = metadata["hash"][0]
        if hashtype == 0x12:
            hashlen = metadata["hash"][1]
            hash_of_sbx_file_decoded = metadata["hash"][2:2+hashlen]  
            d = hashlib.sha256()
    if hash_of_sbx_file_decoded == getsha256(path_to_file.split(".sbx")[0]):
        return True
    return False

    
    #Creates shielded File in the mirror directory
def create_shielded_version_of_file(path_to_file):
    #check if hash is equal
    if path_to_file.endswith(".sbx"):
        if check_integrity(path_to_file):
            return           
        print("Hash of Files dont match")
    print("PATH:",path_to_file)
    print("Creating shielded version of File")
    #copying File
       
    #shutil.copyfile(path_to_file,path_to_file+".sbx")
    #encoding file

    os.system("python RS-SeqBox/sbxenc.py -o "+path_to_file +" "+path_to_file+".sbx")
    print("file encoded")

def unshield_file(path_to_file):
    print("Unshielding file")
    os.system("python RS-SeqBox/sbxdec.py -o"+path_to_file)



class Operations(pyfuse3.Operations):

    enable_writeback_cache = True

    def __init__(self, source, access_dir):
        super().__init__()
        self._inode_path_map = { pyfuse3.ROOT_INODE: source }
        print("access_dir: ", access_dir)
        self.access_dir=access_dir
        self._lookup_cnt = defaultdict(lambda : 0)
        self._fd_inode_map = dict()
        self._inode_fd_map = dict()
        self._fd_open_count = dict()
        self.path_to_file = ""

    
    

    def _inode_to_path(self, inode):
        try:
            val = self._inode_path_map[inode]
        except KeyError:
            raise FUSEError(errno.ENOENT)

        if isinstance(val, set):
            # In case of hardlinks, pick any path
            val = next(iter(val))
        print("inode to path ", val)
        return val

    def _add_path(self, inode, path):
        print("_adding path?")
        log.debug('_add_path for %d, %s', inode, path)
        self._lookup_cnt[inode] += 1

        # With hardlinks, one inode may map to multiple paths.
        if inode not in self._inode_path_map:
            self._inode_path_map[inode] = path
            return

        val = self._inode_path_map[inode]
        if isinstance(val, set):
            val.add(path)
        elif val != path:
            self._inode_path_map[inode] = { path, val }

    async def forget(self, inode_list):
        for (inode, nlookup) in inode_list:
            if self._lookup_cnt[inode] > nlookup:
                self._lookup_cnt[inode] -= nlookup
                continue
            log.debug('forgetting about inode %d', inode)
            assert inode not in self._inode_fd_map
            del self._lookup_cnt[inode]
            try:
                del self._inode_path_map[inode]
            except KeyError: # may have been deleted
                pass

    async def lookup(self, inode_p, name, ctx=None):
        name = fsdecode(name)
        log.debug('lookup for %s in %d', name, inode_p)
        path = os.path.join(self._inode_to_path(inode_p), name)
        attr = self._getattr(path=path)
        if name != '.' and name != '..':
            self._add_path(attr.st_ino, path)
        return attr

    async def getattr(self, inode, ctx=None):
        if inode in self._inode_fd_map:
            return self._getattr(fd=self._inode_fd_map[inode])
        else:
            return self._getattr(path=self._inode_to_path(inode))

    def _getattr(self, path=None, fd=None):
        assert fd is None or path is None
        assert not(fd is None and path is None)
        try:
            if fd is None:
                stat = os.lstat(path)
            else:
                stat = os.fstat(fd)
        except OSError as exc:
            raise FUSEError(exc.errno)

        entry = pyfuse3.EntryAttributes()
        for attr in ('st_ino', 'st_mode', 'st_nlink', 'st_uid', 'st_gid',
                     'st_rdev', 'st_size', 'st_atime_ns', 'st_mtime_ns',
                     'st_ctime_ns'):
            setattr(entry, attr, getattr(stat, attr))
        entry.generation = 0
        entry.entry_timeout = 0
        entry.attr_timeout = 0
        entry.st_blksize = 512
        entry.st_blocks = ((entry.st_size+entry.st_blksize-1) // entry.st_blksize)

        return entry

    async def readlink(self, inode, ctx):
        path = self._inode_to_path(inode)
        print("readlink")
        print(path)
        print(inode)
        try:
            target = os.readlink(path)
            print("target: ",target)
        except OSError as exc:
            raise FUSEError(exc.errno)
        return fsencode(target)

    async def opendir(self, inode, ctx):
        return inode

    async def readdir(self, inode, off, token):
        path = self._inode_to_path(inode)
        log.debug('reading %s', path)
        entries = []
        for name in os.listdir(path):
            if name == '.' or name == '..' or name.endswith(".sb.rs"):
                continue
            attr = self._getattr(path=os.path.join(path, name))
            entries.append((attr.st_ino, name, attr))

        log.debug('read %d entries, starting at %d', len(entries), off)

        # This is not fully posix compatible. If there are hardlinks
        # (two names with the same inode), we don't have a unique
        # offset to start in between them. Note that we cannot simply
        # count entries, because then we would skip over entries
        # (or return them more than once) if the number of directory
        # entries changes between two calls to readdir().
        for (ino, name, attr) in sorted(entries):
            if ino <= off:
                continue
            if not pyfuse3.readdir_reply(
                token, fsencode(name), attr, ino):
                break
            self._add_path(attr.st_ino, os.path.join(path, name))

    async def unlink(self, inode_p, name, ctx):
        name = fsdecode(name)
        parent = self._inode_to_path(inode_p)
        path = os.path.join(parent, name)
        try:
            inode = os.lstat(path).st_ino
            os.unlink(path)
            os.unlink(path+".sb.rs")
        except OSError as exc:
            raise FUSEError(exc.errno)
        if inode in self._lookup_cnt:
            self._forget_path(inode, path)

    async def rmdir(self, inode_p, name, ctx):
        name = fsdecode(name)
        parent = self._inode_to_path(inode_p)
        path = os.path.join(parent, name)
        try:
            inode = os.lstat(path).st_ino
            print("rmdir path",path)
            os.rmdir(path)
        except OSError as exc:
            raise FUSEError(exc.errno)
        if inode in self._lookup_cnt:
            self._forget_path(inode, path)

    def _forget_path(self, inode, path):
        print("forget path")
        print(inode)
        print(path)
        log.debug('forget %s for %d', path, inode)
        val = self._inode_path_map[inode]
        if isinstance(val, set):
            val.remove(path)
            if len(val) == 1:
                self._inode_path_map[inode] = next(iter(val))
        else:
            del self._inode_path_map[inode]

    async def symlink(self, inode_p, name, target, ctx):
        print("symlink")
        print(inode_p)
        print(name)
        print(target)

        name = fsdecode(name)
        target = fsdecode(target)
        parent = self._inode_to_path(inode_p)
        path = os.path.join(parent, name)
        try:
            os.symlink(target, path)
            os.symlink(target+".sb.rs",path+".sb.rs")
            os.chown(path, ctx.uid, ctx.gid, follow_symlinks=False)
            os.chown(path+".sb.rs", ctx.uid, ctx.gid, follow_symlinks=False)
        except OSError as exc:
            raise FUSEError(exc.errno)
        stat = os.lstat(path)
        self._add_path(stat.st_ino, path)
        return await self.getattr(stat.st_ino)

    async def rename(self, inode_p_old, name_old, inode_p_new, name_new,
                     flags, ctx):
        if flags != 0:
            raise FUSEError(errno.EINVAL)

        name_old = fsdecode(name_old)
        name_new = fsdecode(name_new)
        parent_old = self._inode_to_path(inode_p_old)
        parent_new = self._inode_to_path(inode_p_new)
        path_old = os.path.join(parent_old, name_old)
        path_new = os.path.join(parent_new, name_new)
        try:
            os.rename(path_old, path_new)
            os.rename(path_old+".sb.rs",path_new+".sb.rs")
            inode = os.lstat(path_new).st_ino
        except OSError as exc:
            raise FUSEError(exc.errno)
        if inode not in self._lookup_cnt:
            return

        val = self._inode_path_map[inode]
        if isinstance(val, set):
            assert len(val) > 1
            val.add(path_new)
            val.remove(path_old)
        else:
            assert val == path_old
            self._inode_path_map[inode] = path_new

    async def link(self, inode, new_inode_p, new_name, ctx):
        print("link")
        print(inode)
        print(new_inode_p)
        print(new_name)
        new_name = fsdecode(new_name)
        parent = self._inode_to_path(new_inode_p)
        path = os.path.join(parent, new_name)
        try:
            os.link(self._inode_to_path(inode), path, follow_symlinks=False)
            os.link(self._inode_to_path(inode)+".sb.rs",path+".sb.rs",follow_symlinks=False)
        except OSError as exc:
            raise FUSEError(exc.errno)
        self._add_path(inode, path)
        return await self.getattr(inode)

    async def setattr(self, inode, attr, fields, fh, ctx):
        # We use the f* functions if possible so that we can handle
        # a setattr() call for an inode without associated directory
        # handle.
        if fh is None:
            path_or_fh = self._inode_to_path(inode)
            truncate = os.truncate
            chmod = os.chmod
            chown = os.chown
            stat = os.lstat
        else:
            path_or_fh = fh
            truncate = os.ftruncate
            chmod = os.fchmod
            chown = os.fchown
            stat = os.fstat

        try:
            if fields.update_size:
                truncate(path_or_fh, attr.st_size)

            if fields.update_mode:
                # Under Linux, chmod always resolves symlinks so we should
                # actually never get a setattr() request for a symbolic
                # link.
                assert not stat_m.S_ISLNK(attr.st_mode)
                chmod(path_or_fh, stat_m.S_IMODE(attr.st_mode))

            if fields.update_uid:
                chown(path_or_fh, attr.st_uid, -1, follow_symlinks=False)

            if fields.update_gid:
                chown(path_or_fh, -1, attr.st_gid, follow_symlinks=False)

            if fields.update_atime and fields.update_mtime:
                if fh is None:
                    os.utime(path_or_fh, None, follow_symlinks=False,
                             ns=(attr.st_atime_ns, attr.st_mtime_ns))
                else:
                    os.utime(path_or_fh, None,
                             ns=(attr.st_atime_ns, attr.st_mtime_ns))
            elif fields.update_atime or fields.update_mtime:
                # We can only set both values, so we first need to retrieve the
                # one that we shouldn't be changing.
                oldstat = stat(path_or_fh)
                if not fields.update_atime:
                    attr.st_atime_ns = oldstat.st_atime_ns
                else:
                    attr.st_mtime_ns = oldstat.st_mtime_ns
                if fh is None:
                    os.utime(path_or_fh, None, follow_symlinks=False,
                             ns=(attr.st_atime_ns, attr.st_mtime_ns))
                else:
                    os.utime(path_or_fh, None,
                             ns=(attr.st_atime_ns, attr.st_mtime_ns))

        except OSError as exc:
            raise FUSEError(exc.errno)

        return await self.getattr(inode)

    async def mknod(self, inode_p, name, mode, rdev, ctx):
        print("MKNOD")
        print(name)
        print(mode)
        print(inode_p)
        path = os.path.join(self._inode_to_path(inode_p), fsdecode(name))
        try:
            os.mknod(path, mode=(mode & ~ctx.umask), device=rdev)
            os.chown(path, ctx.uid, ctx.gid)
        except OSError as exc:
            raise FUSEError(exc.errno)
        attr = self._getattr(path=path)
        self._add_path(attr.st_ino, path)
        return attr

    async def mkdir(self, inode_p, name, mode, ctx):
        path = os.path.join(self._inode_to_path(inode_p), fsdecode(name))
        try:
            os.mkdir(path, mode=(mode & ~ctx.umask))
            os.chown(path, ctx.uid, ctx.gid)
        except OSError as exc:
            raise FUSEError(exc.errno)
        attr = self._getattr(path=path)
        self._add_path(attr.st_ino, path)
        return attr

    async def statfs(self, ctx):
        root = self._inode_path_map[pyfuse3.ROOT_INODE]
        stat_ = pyfuse3.StatvfsData()
        try:
            statfs = os.statvfs(root)
        except OSError as exc:
            raise FUSEError(exc.errno)
        for attr in ('f_bsize', 'f_frsize', 'f_blocks', 'f_bfree', 'f_bavail',
                     'f_files', 'f_ffree', 'f_favail'):
            setattr(stat_, attr, getattr(statfs, attr))
        stat_.f_namemax = statfs.f_namemax - (len(root)+1)
        return stat_

    async def open(self, inode, flags, ctx):
        if inode in self._inode_fd_map:
            fd = self._inode_fd_map[inode]
            self._fd_open_count[fd] += 1
            return pyfuse3.FileInfo(fh=fd)
        assert flags & os.O_CREAT == 0
        try:
            fd = os.open(self._inode_to_path(inode), flags)
        except OSError as exc:
            raise FUSEError(exc.errno)
        self._inode_fd_map[inode] = fd
        self._fd_inode_map[fd] = inode
        self._fd_open_count[fd] = 1
        return pyfuse3.FileInfo(fh=fd)

    async def create(self, inode_p, name, mode, flags, ctx):
        #after creating a file, the mirrored version should be shielded
        #--
        
        print(name)
        print(mode)
        print(inode_p)
        print(self._inode_to_path(inode_p))
        print(fsdecode(name))
        path = os.path.join(self._inode_to_path(inode_p), fsdecode(name))
        try:
            print(path)
            fd = os.open(path, flags | os.O_CREAT | os.O_TRUNC)
            
        except OSError as exc:
            raise FUSEError(exc.errno)
        attr = self._getattr(fd=fd)
        self._add_path(attr.st_ino, path)
        self._inode_fd_map[attr.st_ino] = fd
        self._fd_inode_map[fd] = attr.st_ino
        self._fd_open_count[fd] = 1
        return (pyfuse3.FileInfo(fh=fd), attr)
    #normal
    async def read(self, fd, offset, length):
       
        #check integrity before reading
        #--
        os.lseek(fd, offset, os.SEEK_SET)
        return os.read(fd, length)
    #normal
    async def write(self, fd, offset, buf):
        #check integrity before writing
        #--
        os.lseek(fd, offset, os.SEEK_SET) 
        return os.write(fd, buf)

    async def release(self, fd):
       
        print("RELEASING")
        #after releasing it was possible that a file was written to - 
        #shielded version should be replace by new file
        #--
        if self._fd_open_count[fd] > 1:
            self._fd_open_count[fd] -= 1
            return

        del self._fd_open_count[fd]
        inode = self._fd_inode_map[fd]
        path_to_file = self._inode_to_path(inode)
        print("type: ",type(path_to_file))


        #print("path0 ",path_to_file[0])
        #print("path1 ",path_to_file[1])

        del self._inode_fd_map[inode]
        del self._fd_inode_map[fd]
        try:
            print("file is here", self._inode_to_path(inode))
            os.close(fd)
            self.path_to_file = path_to_file
            create_shielded_version_of_file(path_to_file)
        
        except OSError as exc:
            raise FUSEError(exc.errno)

def init_logging(debug=False):
    formatter = logging.Formatter('%(asctime)s.%(msecs)03d %(threadName)s: '
                                  '[%(name)s] %(message)s', datefmt="%Y-%m-%d %H:%M:%S")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    if debug:
        handler.setLevel(logging.DEBUG)
        root_logger.setLevel(logging.DEBUG)
    else:
        handler.setLevel(logging.INFO)
        root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)


def parse_args(args):
    '''Parse command line'''

    parser = ArgumentParser()

    parser.add_argument('source', type=str,
                        help='Directory tree to mirror data -> shield Data')
    parser.add_argument('mountpoint', type=str,
                        help='Where to mount the file system - All files There will be shielded')
    parser.add_argument('--debug', action='store_true', default=False,
                        help='Enable debugging output')
    parser.add_argument('--debug-fuse', action='store_true', default=False,
                        help='Enable FUSE debugging output')

    return parser.parse_args(args)

def main():
    #if keyboard interrupt unmount directory

    print(1)
    options = parse_args(sys.argv[1:])
    print(2)
    init_logging(options.debug)
    print(3)
    operations = Operations(options.source,options.mountpoint)

    log.debug('Mounting...')
    print(4)
    fuse_options = set(pyfuse3.default_options)
    print(5)
    fuse_options.add('fsname=Shieldfs')
    print(6)
    if options.debug_fuse:
        print(7)
        fuse_options.add('debug')
        print(8)
    fuse_options.add("auto_unmount")
  
    pyfuse3.init(operations, options.mountpoint, fuse_options)
    print(9)

    try:
        print(10)
        log.debug('Entering main loop..')
        print(11)
        trio.run(pyfuse3.main)
        print(12)
    except:
        pyfuse3.close(unmount=False)
        raise

    log.debug('Unmounting..')
    print(13)
    pyfuse3.close(unmount=True)
    print(14)

if __name__ == '__main__':
    main()