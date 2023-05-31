#!/usr/bin/env python3

#--------------------------------------------------------------------------
# SBXEnc - Sequenced Box container Encoder
#
# Created: 10/02/2017
#
# Copyright (C) 2017 Marco Pontello - http://mark0.net/
#
# Licence:
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#--------------------------------------------------------------------------
from reedsolo import RSCodec, ReedSolomonError
import os
import sys
import hashlib
import argparse
import binascii
from functools import partial
from time import time

import seqbox

PROGRAM_VER = "1.0.2"

def calculate_filenames(filename,sbxfilename):
    max_filename_size = 30
    filename_splitted = os.path.split(filename)[1]
    sbx_filename_splitted = os.path.split(sbxfilename)[1]
    filename_size_conform=""
    sbx_filename_size_conform=""
    if len(filename_splitted) < max_filename_size:

        filename_splitted_dot = filename_splitted.split(".")

        size_of_padding = max_filename_size - len(filename_splitted) 

        filename_splitted_dot[0] += size_of_padding * '_'
        
        for i in range(0,len(filename_splitted_dot)):
            if i == len(filename_splitted_dot)-1:
                    filename_size_conform+= filename_splitted_dot[i]
            else:
                filename_size_conform+= filename_splitted_dot[i]+"."
            
    elif len(filename_splitted) > max_filename_size:
        remove_char_size = len(filename_splitted) - max_filename_size
        filename_splitted_dot = filename_splitted.split(".")
        filename_splitted_dot[0] = filename_splitted_dot[0][:-remove_char_size]

        for i in range(0,len(filename_splitted_dot)):
            if i == len(filename_splitted_dot)-1:
                    filename_size_conform+= filename_splitted_dot[i]
            else:
                filename_size_conform+= filename_splitted_dot[i]+"."

    if len(sbx_filename_splitted) < max_filename_size:

        sbx_filename_splitted_dot = sbx_filename_splitted.split(".")

        size_of_padding = max_filename_size - len(sbx_filename_splitted)

        sbx_filename_splitted_dot[0] = sbx_filename_splitted_dot[0] + size_of_padding * '_' 

        for i in range(0,len(sbx_filename_splitted_dot)):
            if i == len(sbx_filename_splitted_dot)-1:
                sbx_filename_size_conform+= sbx_filename_splitted_dot[i]
            else:
                sbx_filename_size_conform+= sbx_filename_splitted_dot[i]+"."
    
    elif len(sbx_filename_splitted) > max_filename_size:
        remove_char_size = len(sbx_filename_splitted) - max_filename_size
        sbx_filename_splitted_dot = sbx_filename_splitted.split(".")
        sbx_filename_splitted_dot[0] = sbx_filename_splitted_dot[0][:-remove_char_size]

        for i in range(0,len(sbx_filename_splitted_dot)):
            if i == len(sbx_filename_splitted_dot)-1:
                sbx_filename_size_conform+= sbx_filename_splitted_dot[i]
            else:
                sbx_filename_size_conform+= sbx_filename_splitted_dot[i]+"."

    if len(sbx_filename_size_conform) == 0:
        sbx_filename_size_conform = sbxfilename
    if len(filename_size_conform) == 0 :
        filename_size_conform = filename

    return filename_size_conform,sbx_filename_size_conform

def calculate_size_of_padding_last_block(filesize):
    rsc=RSCodec(34)
    raw_data_size_read_into_1_block=426
    size_of_data_last_block=filesize%raw_data_size_read_into_1_block

    result= bytes(rsc.encode(size_of_data_last_block*b'A'))

    blocksize=512

    headersize=16

    redundancy_data_addition=len(result)-size_of_data_last_block

    length_of_padding=blocksize-size_of_data_last_block - headersize - redundancy_data_addition
    return length_of_padding

def get_cmdline():
    """Evaluate command line parameters, usage & help."""
    parser = argparse.ArgumentParser(
             description="create a SeqBox container",
             formatter_class=argparse.ArgumentDefaultsHelpFormatter,
             prefix_chars='-+')
    parser.add_argument("-v", "--version", action='version', 
                        version='SeqBox - Sequenced Box container - ' +
                        'Encoder v%s - (C) 2017 by M.Pontello' % PROGRAM_VER) 
    parser.add_argument("filename", action="store", 
                        help="file to encode")
    parser.add_argument("sbxfilename", action="store", nargs='?',
                        help="SBX container")
    parser.add_argument("-o", "--overwrite", action="store_true", default=False,
                        help="overwrite existing file")
    parser.add_argument("-nm","--nometa", action="store_true", default=False,
                        help="exclude matadata block")
    parser.add_argument("-uid", action="store", default="r", type=str,
                        help="use random or custom UID (up to 12 hexdigits)")
    
    parser.add_argument("-sv", "--sbxver", type=int, default=1,
                        help="SBX blocks version", metavar="n")
    parser.add_argument("-p", "--password", type=str, default="",
                        help="encrypt with password", metavar="pass")
    res = parser.parse_args()
    return res

def errexit(errlev=1, mess=""):
    """Display an error and exit."""
    if mess != "":
        sys.stderr.write("%s: error: %s\n" %
                         (os.path.split(sys.argv[0])[1], mess))
    sys.exit(errlev)
    
def getsha256(filename):
    """SHA256 used to verify the integrity of the encoded file"""
    with open(filename, mode='rb') as fin:
        d = hashlib.sha256()
        for buf in iter(partial(fin.read, 1024*1024), b''):
            d.update(buf)
    return d.digest()

def encode(filename,overwrite="False",nometa=False,uid="r",sbxver=1,password=""):

    filename = filename
    sbxfilename = sbxfilename
    if not sbxfilename:
        sbxfilename = os.path.split(filename)[1] + ".sbx"
    elif os.path.isdir(sbxfilename):
        sbxfilename = os.path.join(sbxfilename,
                                   os.path.split(filename)[1] + ".sbx")
    if os.path.exists(sbxfilename) and not overwrite:
        errexit(1, "SBX file '%s' already exists!" % (sbxfilename))
    #parse eventual custom uid
    
    if uid !="r":
        uid = uid[-12:]
        try:
            uid = int(uid, 16).to_bytes(6, byteorder='big')
        except:
            errexit(1, "invalid UID")

    if not os.path.exists(filename):
        errexit(1, "file '%s' not found" % (filename))
    filesize = os.path.getsize(filename)
    fout = open(sbxfilename, "wb", buffering=1024*1024)

    #calc hash - before all processing, and not while reading the file,
    #just to be cautious
    if not nometa:
        print("hashing file '%s'..." % (filename))
        sha256 = getsha256(filename)
        print("SHAA",sha256)
        print("SHA256",binascii.hexlify(sha256).decode())
    print("fin:", filename)
    fin = open(filename, "rb", buffering=1024*1024)
    print("creating file '%s'..." % sbxfilename)

    sbx = seqbox.SbxBlock(uid=uid, ver=sbxver, pswd=password)

    length_of_padding=calculate_size_of_padding_last_block(filesize)
    #write metadata block 0
    filename_size_conform,sbxfilename_size_conform = calculate_filenames(filename,sbxfilename)


    if not nometa:
        sbx.metadata = {"filesize":filesize,
                        "filename":filename_size_conform,
                        "sbxname":sbxfilename_size_conform,
                        "filedatetime":int(os.path.getmtime(filename)),
                        "sbxdatetime":int(time()),
                        "hash":b'\x12\x20'+sha256,#multihash
                        "padding_last_block":length_of_padding} 
        fout.write(sbx.encode())
    
    #write all other blocks
    ticks = 0
    updatetime = time() 
    blocknumber=0
    while True:
        blocknumber = blocknumber+1
        #buffer read is reduced to compensate added redundancy data 32 redundancy adds 64 bytes -> x*2
        buffer = fin.read(sbx.datasize-70)
      
        if len(buffer) < sbx.datasize:
            if len(buffer) == 0:
                break
        sbx.blocknum += 1
        #encode buffer with rsc
        sbx.data = buffer
        fout.write(sbx.encode())

        #some progress update
        if time() > updatetime:
            print("%.1f%%" % (fin.tell()*100.0/filesize), " ",
                  end="\r", flush=True)
            updatetime = time() + .1
        
    print("100%  ")
    fin.close()
    fout.close()

    totblocks = sbx.blocknum if nometa else sbx.blocknum + 1
    sbxfilesize = totblocks * sbx.blocksize
    overhead = 100.0 * sbxfilesize / filesize - 100 if filesize > 0 else 0
    print("SBX file size: %i - blocks: %i - overhead: %.1f%%" %
          (sbxfilesize, totblocks, overhead))

def main():
    cmdline = get_cmdline()
    filename = cmdline.filename
    sbxfilename = cmdline.sbxfilename
    if not sbxfilename:
        sbxfilename = os.path.split(filename)[1] + ".sbx"
    elif os.path.isdir(sbxfilename):
        sbxfilename = os.path.join(sbxfilename,
                                   os.path.split(filename)[1] + ".sbx")
    if os.path.exists(sbxfilename) and not cmdline.overwrite:
        errexit(1, "SBX file '%s' already exists!" % (sbxfilename))
    #parse eventual custom uid
    
    if cmdline.uid !="r":
        uid = uid[-12:]
        try:
            uid = int(uid, 16).to_bytes(6, byteorder='big')
        except:
            errexit(1, "invalid UID")

    if not os.path.exists(filename):
        errexit(1, "file '%s' not found" % (filename))
    filesize = os.path.getsize(filename)
    fout = open(sbxfilename, "wb", buffering=1024*1024)

    #calc hash - before all processing, and not while reading the file,
    #just to be cautious
    if not cmdline.nometa:
        print("hashing file '%s'..." % (filename))
        sha256 = getsha256(filename)
        print("SHAA",sha256)
        print("SHA256",binascii.hexlify(sha256).decode())
    print("fin:", filename)
    fin = open(filename, "rb", buffering=1024*1024)
    print("creating file '%s'..." % sbxfilename)

    sbx = seqbox.SbxBlock(uid=cmdline.uid, ver=cmdline.sbxver, pswd=cmdline.password)

    length_of_padding=calculate_size_of_padding_last_block(filesize)
    #write metadata block 0
    filename_size_conform,sbxfilename_size_conform = calculate_filenames(filename,sbxfilename)


    if not cmdline.nometa:
        sbx.metadata = {"filesize":filesize,
                        "filename":filename_size_conform,
                        "sbxname":sbxfilename_size_conform,
                        "filedatetime":int(os.path.getmtime(filename)),
                        "sbxdatetime":int(time()),
                        "hash":b'\x12\x20'+sha256,#multihash
                        "padding_last_block":length_of_padding} 
        fout.write(sbx.encode())
    
    #write all other blocks
    ticks = 0
    updatetime = time() 
    blocknumber=0
    while True:
        blocknumber = blocknumber+1
        #buffer read is reduced to compensate added redundancy data 32 redundancy adds 64 bytes -> x*2
        buffer = fin.read(sbx.datasize-70)
      
        if len(buffer) < sbx.datasize:
            if len(buffer) == 0:
                break
        sbx.blocknum += 1
        #encode buffer with rsc
        sbx.data = buffer
        fout.write(sbx.encode())

        #some progress update
        if time() > updatetime:
            print("%.1f%%" % (fin.tell()*100.0/filesize), " ",
                  end="\r", flush=True)
            updatetime = time() + .1
        
    print("100%  ")
    fin.close()
    fout.close()

    totblocks = sbx.blocknum if cmdline.nometa else sbx.blocknum + 1
    sbxfilesize = totblocks * sbx.blocksize
    overhead = 100.0 * sbxfilesize / filesize - 100 if filesize > 0 else 0
    print("SBX file size: %i - blocks: %i - overhead: %.1f%%" %
          (sbxfilesize, totblocks, overhead))    


if __name__ == '__main__':
    main()
