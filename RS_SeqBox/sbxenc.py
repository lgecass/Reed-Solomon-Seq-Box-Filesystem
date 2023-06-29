#!/usr/bin/env python3

#----------------------------------------------------------------------------------
#MIT License
#
#Copyright (c) 2023 Lukas Gecas
#
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#
#The above copyright notice and this permission notice shall be included in all
#copies or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#SOFTWARE.
#A part of this Software is based on the work of Marco Pontello
#The base is located at https://github.com/MarcoPon/SeqBox/
#----------------------------------------------------------------------------------

import creedsolo.creedsolo as crs
import os
import sys
import hashlib
import argparse
import binascii
from functools import partial
from time import time as gettime
import shutil

try:
    import RS_SeqBox.seqbox as seqbox
except ImportError:
    pass
try:
    import seqbox as seqbox
except ImportError:
    pass

PROGRAM_VER = "1.0.2"

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
    parser.add_argument("-uid", action="store", default="r", type=str,
                        help="use random or custom UID (up to 12 hexdigits)")
    parser.add_argument("sbxfilename", action="store", nargs='?',
                        help="SBX container")
    parser.add_argument("-p", "--password", type=str, default="",
                        help="encrypt with password", metavar="pass")
    parser.add_argument("-o", "--overwrite", action="store_true", default=False,
                        help="overwrite existing file")
    parser.add_argument("-sv", "--sbxver", type=int, default=1,
                        help="SBX blocks version", metavar="n")
    parser.add_argument("-raid", "--raid", action="store_true", default=False,
                        help="Create duplicate sbx File for better recovery")
    parser.add_argument("-verbose", "--verbose", action="store_true", default=False, help="Show extended Information")
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

def encode(filename,sbxfilename=None,overwrite="False",uid="r",sbx_ver=1, raid=False):
    #filename to encode
    filename = filename
    
    #filename which results from encoding
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
    sha256 = getsha256(filename)

    fin = open(filename, "rb", buffering=1024*1024)
    print("creating file '%s'..." % sbxfilename)

    sbx = seqbox.SbxBlock(uid=uid, ver=sbx_ver)

    #write metadata block 0
    sbx.metadata = {"filesize":filesize,
                        "filename":filename,
                        "sbxname":sbxfilename,
                        "filedatetime":int(os.path.getmtime(filename)),
                        "sbxdatetime":int(gettime()),
                        "hash":b'\x12\x20'+sha256,#multihash
                        "padding_last_block":0,} 
    
    fout.write(sbx.encode())
    
    #write all other blocks
    updatetime = gettime() 
    time_list=[]
    while True:
        #Reads data from file 
        buffer = fin.read(sbx.raw_data_size_read_into_1_block)
        #check if last block or file ended
        if len(buffer) < sbx.raw_data_size_read_into_1_block:
            #if file ended and no more data to be read:
            if len(buffer) == 0:
                #save sbx_blocknum
                sbx_blocknum_save = sbx.blocknum
                #set to 0 so when encoding the data will be treated as header block data
                sbx.blocknum = 0
                #get Header Block behaviour to replace the header block with padding information
                header_block = sbx.encode()
                #close filehandler which was used to write output
                fout.close()
                #replace first 512 Bytes with up to date Informationen
                with open(sbxfilename,'r+b') as f:
                    #go to position 0 in file
                    f.seek(0)
                    #write correct header block
                    f.write(header_block)
                    f.close()
                    #restore blocknum
                    sbx.blocknum = sbx_blocknum_save
                    break
            else:
                #this occurs when the last block is read in | datasize is between 1 byte to sbx.datasize-sbx.redsize
                
                #we set the correct padding in metadata
                sbx.metadata["padding_last_block"] = ((sbx.datasize-sbx.redsize) - len(buffer))
                #fill buffer up with padding
                buffer += b'\x1A'* ((sbx.datasize-sbx.redsize) - len(buffer))

           
        sbx.blocknum += 1
        sbx.data = buffer
        #measure time  
        START_TIME = gettime()

        data = sbx.encode()
        
        #calculate time 
        time_list.append(gettime() - START_TIME)
        #write to file
        fout.write(data)
        
        #some progress update
        if gettime() > updatetime:
            print("%.1f%%" % (fin.tell()*100.0/filesize), " ",
                  end="\r", flush=True)
            updatetime = gettime() + .1
    if raid:
        shutil.copy2(sbxfilename, sbxfilename+".raid")
        
    time_taken = 0
    for time in time_list:
        time_taken += time
    print("total time for Encoding: ", str(time_taken)+ " s")
    print("100%  ")
    fin.close()
    fout.close()

    totblocks = sbx.blocknum if False else sbx.blocknum + 1
    sbxfilesize = totblocks * sbx.blocksize
    overhead = 100.0 * sbxfilesize / filesize - 100 if filesize > 0 else 0
    print("SBX file size: %i - blocks: %i - overhead: %.1f%%" %
          (sbxfilesize, totblocks, overhead))

def main():
    cmdline = get_cmdline()
    #filename to encode
    filename = cmdline.filename
    #filename which results from encoding
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
    sha256 = getsha256(filename)

    fin = open(filename, "rb", buffering=1024*1024)
    print("creating file '%s'..." % sbxfilename)

    sbx = seqbox.SbxBlock(uid=cmdline.uid, ver=cmdline.sbxver, pswd=cmdline.password)

    #write metadata block 0
    sbx.metadata = {"filesize":filesize,
                        "filename":filename,
                        "sbxname":sbxfilename,
                        "filedatetime":int(os.path.getmtime(filename)),
                        "sbxdatetime":int(gettime()),
                        "hash":b'\x12\x20'+sha256,#multihash
                        "padding_last_block":0,} 
    
    fout.write(sbx.encode())
    
    #write all other blocks
    updatetime = gettime() 
    time_list=[]
    
    if cmdline.password:
        encdec = seqbox.EncDec(cmdline.password, sbx.raw_data_size_read_into_1_block)

    while True:
        #Reads data from file 
        buffer = fin.read(sbx.raw_data_size_read_into_1_block)
        
        
        #check if last block or file ended
        if len(buffer) < sbx.raw_data_size_read_into_1_block:
            #if file ended and no more data to be read:
            if len(buffer) == 0:
                #save sbx_blocknum
                sbx_blocknum_save = sbx.blocknum
                #set to 0 so when encoding the data will be treated as header block data
                sbx.blocknum = 0
                #get Header Block behaviour to replace the header block with padding information
                header_block = sbx.encode()
                #close filehandler which was used to write output
                fout.close()
                #replace first 512 Bytes with up to date Informationen
                with open(sbxfilename,'r+b') as f:
                    #go to position 0 in file
                    f.seek(0)
                    #write correct header block
                    f.write(header_block)
                    f.close()
                    #restore blocknum
                    sbx.blocknum = sbx_blocknum_save
                    break
            else:
                #this occurs when the last block is read in | datasize is between 1 byte to sbx.datasize-sbx.redsize
                
                #we set the correct padding in metadata
                sbx.metadata["padding_last_block"] = ((sbx.datasize-sbx.redsize) - len(buffer))
                #fill buffer up with padding
                buffer += b'\x1A'* ((sbx.datasize-sbx.redsize) - len(buffer))

        if cmdline.password:
            buffer = encdec.xor(buffer)   

        sbx.blocknum += 1
        sbx.data = buffer

        data = sbx.encode()
       
        #write to file
        fout.write(data)
        
        #some progress update
        if gettime() > updatetime:
            print("%.1f%%" % (fin.tell()*100.0/filesize), " ",
                  end="\r", flush=True)
            updatetime = gettime() + .1
    if cmdline.raid:
        print("Copying sbx file")
        shutil.copy2(sbxfilename, sbxfilename+".raid")

    print("100%  ")
    fin.close()
    fout.close()

    totblocks = sbx.blocknum if False else sbx.blocknum + 1
    sbxfilesize = totblocks * sbx.blocksize
    overhead = 100.0 * sbxfilesize / filesize - 100 if filesize > 0 else 0
    print("SBX file size: %i - blocks: %i - overhead: %.1f%%" %
          (sbxfilesize, totblocks, overhead))


    

if __name__ == '__main__':
    main()
