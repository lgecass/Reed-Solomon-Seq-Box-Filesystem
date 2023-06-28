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
import RS_SeqBox.sbxenc as sbxenc
import RS_SeqBox.sbxdec as sbxdec
import RS_SeqBox.seqbox as seqbox
import creedsolo.creedsolo as crs


import faulthandler
faulthandler.enable()

log = logging.getLogger(__name__)

active_sbx_encodings = []
def decode_header_block_with_rsc(buffer, sbx_version):
    sbx = seqbox.SbxBlock(ver=sbx_version)
    rsc=crs.RSCodec(sbx.redsym)
    decoded = bytes(rsc.decode(bytearray(buffer[:-sbx.padding_normal_block]))[0])
    return decoded

def check_if_sbx_file_exists(path_of_normal_file):
    return os.path.exists(path_of_normal_file+".sbx")

def compare_hash_sbxfile_normalfile(normal_file_hash,sbx_file_hash):
    if normal_file_hash == sbx_file_hash:
        return True
    return False

def get_hash_of_normal_file(path_to_file):
    """SHA256 used to verify the integrity of the encoded file"""
    with open(path_to_file, mode='rb') as fin:
        d = hashlib.sha256()
        for buf in iter(partial(fin.read, 1024*1024), b''):
            d.update(buf)
    return d.digest()

#Checks integrity of any File  
def get_hash_of_sbx_file(path_to_file, sbx_version, raid):
    print("Checking integrity of ", path_to_file)
    if not os.path.exists(path_to_file):
        print(1, "sbx file '%s' not found" % (path_to_file))
        return
    
    sbx = seqbox.SbxBlock(ver=sbx_version)
    fin = open(path_to_file, "rb", buffering=1024*1024)
    
    raid_exists = os.path.exists(path_to_file+".raid") and raid == True
    if raid_exists:
        fin_raid = open(path_to_file+".raid", "rb", buffering=1024*1024)
        fin_raid.seek(0,0)
        buffer_raid = fin_raid.read(sbx.blocksize)
        fin_raid.close()
    
    buffer = fin.read(sbx.blocksize)
    fin.close()
    try:
        buffer = bytes(decode_header_block_with_rsc(buffer, sbx_version))
    except crs.ReedSolomonError:
        if raid_exists:
            try:
                buffer=bytes(decode_header_block_with_rsc(buffer_raid,sbx_version))
            except crs.ReedSolomonError:
                pass


    header = buffer[:3]

    data = buffer[16:]
    if header[:3] != b"SBx":
        print(1, "not a SeqBox file!")
        return
    metadata = {}
    p=0
    while p < (len(data)-3):
                metaid = data[p:p+3]
                p+=3
                if metaid == b"\x1a\x1a\x1a":
                    break
                else:
                    metalen = data[p]
                    metabb = data[p+1:p+1+metalen]
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
                        break
    if "hash" in metadata:
        hashtype = metadata["hash"][0]
        if hashtype == 0x12:
            hashlen = metadata["hash"][1]
            hash_of_sbx_file_decoded = metadata["hash"][2:2+hashlen]  
            d = hashlib.sha256()
            return hash_of_sbx_file_decoded
    else:
        return ""
    #Creates shielded File in the mirror directory
def create_shielded_version_of_file(path_to_file, sbx_version, raid):
    #check if hash is equal
    sbx = seqbox.SbxBlock(ver=sbx_version)

    if path_to_file.endswith(".sbx"):
        if not os.path.exists(path_to_file.split(".sbx")[0]):
            sbxdec.decode(path_to_file, sbx_ver=sbx.ver, raid=raid)
            active_sbx_encodings.remove(path_to_file)
            return

        if get_hash_of_sbx_file(path_to_file, sbx_ver=sbx_version, raid=raid) == get_hash_of_normal_file(path_to_file.split(".sbx")[0]):
            print("Hash of Files dont match")
            sbxdec.decode(path_to_file,sbx_ver=sbx.ver, raid=raid)
            active_sbx_encodings.remove(path_to_file)
            return
        else:
            return
    print("Creating shielded version of File")
    sbxenc.encode(path_to_file,sbxfilename=path_to_file+".sbx", sbx_ver=sbx.ver, raid=raid)    
    print("file encoded")
    active_sbx_encodings.remove(path_to_file)


def unshield_file(path_to_file, sbx_version, raid):
    print("Unshielding file")
    sbxdec.decode(path_to_file+".sbx", overwrite=True, sbx_ver=sbx_version, raid=raid)

class Operations(pyfuse3.Operations):

    enable_writeback_cache = True

    def __init__(self, source, sbx_version,raid):
        self.raid = raid
        super().__init__()
        self.sbx_version = sbx_version
        self.shield_dir=source
        self._inode_path_map = { pyfuse3.ROOT_INODE: source }
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
     
        return val

    def _add_path(self, inode, path):
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
        try:
            target = os.readlink(path)
        except OSError as exc:
            raise FUSEError(exc.errno)
        return fsencode(target)

    async def opendir(self, inode, ctx):
        return inode

    async def readdir(self, inode, off, token):
        path = self._inode_to_path(inode)
        log.debug('reading %s', path)
        entries = []
        if not os.path.exists(path):
            return
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
        log.debug('forget %s for %d', path, inode)
        val = self._inode_path_map[inode]
        if isinstance(val, set):
            val.remove(path)
            if len(val) == 1:
                self._inode_path_map[inode] = next(iter(val))
        else:
            del self._inode_path_map[inode]

    async def symlink(self, inode_p, name, target, ctx):
        name = fsdecode(name)
        target = fsdecode(target)
        parent = self._inode_to_path(inode_p)
        path = os.path.join(parent, name)
        try:
            os.symlink(target, path)
            os.symlink(target+".sbx",path+".sbx")
            os.chown(path, ctx.uid, ctx.gid, follow_symlinks=False)
            os.chown(path+".sbx", ctx.uid, ctx.gid, follow_symlinks=False)
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
        new_name = fsdecode(new_name)
        parent = self._inode_to_path(new_inode_p)
        path = os.path.join(parent, new_name)
        try:
            os.link(self._inode_to_path(inode), path, follow_symlinks=False)
            os.link(self._inode_to_path(inode)+".sbx",path+".sbx",follow_symlinks=False)
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
        #Before file is being read it is first opened
        #check Integrity of file here
        if inode in self._inode_fd_map:
            print("Early when file descriptor already exists")
            fd = self._inode_fd_map[inode]
            self._fd_open_count[fd] += 1
            return pyfuse3.FileInfo(fh=fd)
        assert flags & os.O_CREAT == 0
        try:
            file_path = self._inode_to_path(inode)
            print("TRYING OPEN",file_path)
            if active_sbx_encodings.__contains__(file_path):
                print("active",active_sbx_encodings)
                fd = os.open(file_path, flags)
            else:
                if not file_path.endswith(".sbx"):
                    print("active",active_sbx_encodings)
                    if file_path.__contains__(".trashinfo") or (get_hash_of_normal_file(file_path) == get_hash_of_sbx_file(file_path+".sbx", sbx_version=self.sbx_version)):
                        print("Hashes Match or file being deleted")
                        fd = os.open(file_path, flags)
                    else:
                        print("Hashes dont match")
                        if os.path.exists(file_path+".sbx"):
                            if os.lstat(file_path+".sbx").st_size > 0:
                                unshield_file(file_path, self.sbx_version, self.raid)
                                fd = os.open(file_path, flags)
                        else:
                            print("File does not exist because it is being renamed")
                            fd = os.open(file_path,flags)

                else:
                    fd = os.open(file_path, flags)
        except OSError as exc:
            raise FUSEError(exc.errno)
        self._inode_fd_map[inode] = fd
        self._fd_inode_map[fd] = inode
        self._fd_open_count[fd] = 1
        return pyfuse3.FileInfo(fh=fd)

    async def create(self, inode_p, name, mode, flags, ctx):
        #after creating a file, the mirrored version should be shielded
        #--
        path = os.path.join(self._inode_to_path(inode_p), fsdecode(name))
        try:
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
        if self._fd_open_count[fd] > 1:
            self._fd_open_count[fd] -= 1
            return

        del self._fd_open_count[fd]
        inode = self._fd_inode_map[fd]
        path_to_file = self._inode_to_path(inode)

        del self._inode_fd_map[inode]
        del self._fd_inode_map[fd]
        try:
            os.close(fd)
            self.path_to_file = path_to_file
            #Check if after releasing file, changes to the file have been made
            #if not then it is not neccessary to recreate sbx file
            if not path_to_file.endswith(".sbx"):
                if path_to_file.__contains__(".trashinfo"):
                    return
                if check_if_sbx_file_exists(path_to_file):
                    if get_hash_of_normal_file(path_to_file) != get_hash_of_sbx_file(path_to_file+".sbx",self.sbx_version):
                        if not active_sbx_encodings.__contains__(path_to_file):
                            print("HASHES DONT MATCH")
                            active_sbx_encodings.append(path_to_file)
                            create_shielded_version_of_file(path_to_file, self.sbx_version, self.raid)
                            
                        else:
                            print("File is already being processed")
                    else:
                        print("File was released without changes, no need to create sbx file")
                else:
                    print("Threading")
                    if not active_sbx_encodings.__contains__(path_to_file):
                        active_sbx_encodings.append(path_to_file)
                        create_shielded_version_of_file(path_to_file,self.sbx_version)
                        
        
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
    parser.add_argument("-sv", "--sbxver", type=int, default=1,
                        help="SBX blocks version", metavar="n")
    parser.add_argument("-raid", "--raid", action="store_true", default=False,
                        help="Take .raid files into consideration in encoding/decoding")
    return parser.parse_args(args)

def main():

    
    options = parse_args(sys.argv[1:])
    print("VERSION",options.sbxver)
    
    sbx_versions = [1,2]
    if not sbx_versions.__contains__(options.sbxver):
        exit("Sbxversion "+ str(options.sbxver)+" not available. Version 1 : 512 Byte Blocks, Version 2 : 4096 Byte blocks")
    
    init_logging(options.debug)
    
    
    operations = Operations(options.source, options.sbxver, options.raid)

    log.debug('Mounting...')

    fuse_options = set(pyfuse3.default_options)

    fuse_options.add('fsname=Shieldfs')

    if options.debug_fuse:

        fuse_options.add('debug')

    fuse_options.add("auto_unmount")
  
    pyfuse3.init(operations, options.mountpoint, fuse_options)


    try:

        log.debug('Entering main loop..')

        trio.run(pyfuse3.main)

    except:
        pyfuse3.close(unmount=False)
        raise

    log.debug('Unmounting..')

    pyfuse3.close(unmount=True)


if __name__ == '__main__':
    main()