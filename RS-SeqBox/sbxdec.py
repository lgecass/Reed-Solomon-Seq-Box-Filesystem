#!/usr/bin/env python3

#--------------------------------------------------------------------------
# SBXDec - Sequenced Box container Decoder
#
# Created: 03/03/2017
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
import time

import seqbox

PROGRAM_VER = "1.0.2"

def get_cmdline():
    """Evaluate command line parameters, usage & help."""
    parser = argparse.ArgumentParser(
             description="decode a SeqBox container",
             formatter_class=argparse.ArgumentDefaultsHelpFormatter,
             prefix_chars='-+')
    parser.add_argument("-v", "--version", action='version', 
                        version='SeqBox - Sequenced Box container - ' +
                        'Decoder v%s - (C) 2017 by M.Pontello' % PROGRAM_VER) 
    parser.add_argument("sbxfilename", action="store", help="SBx container")
    parser.add_argument("filename", action="store", nargs='?', 
                        help="target/decoded file")
    parser.add_argument("-t","--test", action="store_true", default=False,
                        help="test container integrity")
    parser.add_argument("-i", "--info", action="store_true", default=False,
                        help="show informations/metadata")
    parser.add_argument("-c", "--continue", action="store_true", default=False,
                        help="continue on block errors", dest="cont")
    parser.add_argument("-o", "--overwrite", action="store_true", default=False,
                        help="overwrite existing file")
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


def lastEofCount(data):
    count = 0
    for b in range(len(data)):
        if data[-b-1] != 0x1a:
            break
        count +=1
    return count
def bruteforce_possible_broken_padding(buffer,redundandcy_rsc_code):
    print("Bruteforcing")
    rsc=RSCodec(redundandcy_rsc_code)
    amplitude=0
    amplitude_minus=0
    i=0
    while True:
        if hex(buffer[i])==hex(26):
                count_of_EOF = i
                print(count_of_EOF)
                print(buffer[i])
                break
        else:           
                i+=1   
    while True:
        try:
            print("amp+",i+amplitude)
            rsc.decode(buffer[:i+amplitude])
           
            print("real buffer+:",buffer[:i+amplitude])
            return i+amplitude
        except ReedSolomonError as err:
            amplitude+=1
            print("Continuing plus")

    

        try:
            print("amp-",i+amplitude_minus)
            rsc.decode(buffer[:i-amplitude_minus])
            print("real buffer-:",buffer[:i-amplitude_minus])
            return i+amplitude_minus
        except ReedSolomonError as err:
            amplitude_minus-=1
            print("Continuing minus")
def decode_data_block_with_rsc(buffer,blocknumber,filesize):
    redundancy=32
    rsc=RSCodec(32)
    blocknumber+=1
    #search for first occurence of "0x1a" and cut to there
    print(blocknumber)
    print(blocknumber*512)
    print(filesize)
    if blocknumber*512+512==filesize:
        if buffer[:-1] != hex(26):
            
            #try to decode
            try:
                rsc_decoded_data_block = buffer[:16]+bytes(rsc.decode(buffer[16:])[0])
                return rsc_decoded_data_block
            except ReedSolomonError as rserr:
                print(rserr)
        print("lastblock")
        
        first_occurence_of_EOF=0
        for i in range(1,len(buffer)):
            if hex(buffer[i]) == hex(26):
                    first_occurence_of_EOF = i
                    break
        if first_occurence_of_EOF == 0:
            #found no EOF - File size fits perfectly
            rsc_decoded_data_block = buffer[:16]+bytes(rsc.decode(buffer[16:])[0])
            return rsc_decoded_data_block
        else:
            
            try:
                print("BUFF",buffer[16:first_occurence_of_EOF])
                rsc_decoded_data_block = buffer[:16]+bytes(rsc.decode(buffer[16:first_occurence_of_EOF])[0])
                
                return rsc_decoded_data_block
            except ReedSolomonError as rserr:
                print(rserr)
                print("Decoding Error, there is maybe a corruption in EOF, trying to repair")
                actual_EOF_offset=bruteforce_possible_broken_padding(buffer[16:],redundancy)
                print("ACTUAL TEST",buffer[16:actual_EOF_offset])
                rsc_decoded_data_block = buffer[:16]+bytes(rsc.decode(buffer[16:actual_EOF_offset])[0])
    else:       
        rsc_decoded_data_block = buffer[:16]+bytes(rsc.decode(buffer[16:])[0])           
    return rsc_decoded_data_block



def decode_header_block_with_rsc(buffer,blocksize):
    
    redundancy=32
    rsc=RSCodec(redundancy)
    broken_padding = False #Padding breaks if at the EOF symbol (\x1A) 1 bit flips

    print(buffer)
    #check where Headerdata ends (EOF(\x1A))
    i=0
    while True:
        if hex(buffer[i])==hex(26):
            count_until_EOF_=i
            break
        else:
            i+=1

    
    try:
        print(buffer[:count_until_EOF_],"\n")
        rsc_decoded = bytes(rsc.decode(buffer[:count_until_EOF_])[0])
        print() 
        rsc_decoded_and_added_padding= rsc_decoded + b'\x1A' * (blocksize-len(rsc_decoded))
        print(rsc_decoded_and_added_padding)
        return rsc_decoded_and_added_padding
    except ReedSolomonError as rserror:
        print("Possible padding broken through corruption, trying bruteforce"+"\n")
        broken_padding=True
        
        bruteforced_offset=bruteforce_possible_broken_padding(buffer,redundancy)  
 



    if broken_padding:
            print("BUFFER",buffer[:bruteforced_offset],"\n")  
            rsc_decoded = bytes(rsc.decode(buffer[:bruteforced_offset])[0])
            print(rsc_decoded,"\n")
            rsc_decoded_and_added_padding= rsc_decoded + b'\x1A' * (blocksize-len(rsc_decoded))
            print(rsc_decoded_and_added_padding)
            return rsc_decoded_and_added_padding

    

    return rsc_decoded_and_added_padding


def main():

    cmdline = get_cmdline()
    
    sbxfilename = cmdline.sbxfilename
    filename = cmdline.filename
    print(sbxfilename)
    print(filename)
    if not os.path.exists(sbxfilename):
        errexit(1, "sbx file '%s' not found" % (sbxfilename))
    sbxfilesize = os.path.getsize(sbxfilename)

    print("decoding '%s'..." % (sbxfilename))
    fin = open(sbxfilename, "rb", buffering=1024*1024)

    #check magic and get version
    header = fin.read(4)
    fin.seek(0, 0)
    if cmdline.password:
        e = seqbox.EncDec(cmdline.password, len(header))
        header= e.xor(header)
    if header[:3] != b"SBx":
        print(header[:3])
        errexit(1, "not a SeqBox file!")
    sbxver = header[3]
    
    sbx = seqbox.SbxBlock(ver=sbxver, pswd=cmdline.password)
    metadata = {}
    trimfilesize = False

    hashtype = 0
    hashlen = 0
    hashdigest = b""
    hashcheck = False

    buffer = fin.read(sbx.blocksize)
    print("HEADER")
    buffer=decode_header_block_with_rsc(buffer,blocksize=sbx.blocksize)

    sbx.decode(buffer)
    if sbx.blocknum > 1:
        errexit(errlev=1, mess="blocks missing or out of order at offset 0x0")
    elif sbx.blocknum == 0:
        print("metadata block found!")
        metadata = sbx.metadata
        if "filesize" in metadata:
            trimfilesize = True
        if "hash" in metadata:
            hashtype = metadata["hash"][0]
            if hashtype == 0x12:
                hashlen = metadata["hash"][1]
                hashdigest = metadata["hash"][2:2+hashlen]
                hashcheck = True
        
    else:
        #first block is data, so reset from the start
        print("no metadata available")
        fin.seek(0, 0)

    #display some info and stop
    if cmdline.info:
        print("\nSeqBox container info:")
        print("  file size: %i bytes" % (sbxfilesize))
        print("  blocks: %i" % (sbxfilesize / sbx.blocksize))
        print("  version: %i" % (sbx.ver))
        print("  UID: %s" % (binascii.hexlify(sbx.uid).decode()))
        if metadata:
            print("metadata:")
            if "sbxname" in metadata:
                print("  SBX name : '%s'" % (metadata["sbxname"]))
            if "filename" in metadata:
                print("  file name: '%s'" % (metadata["filename"]))
            if "filesize" in metadata:
                print("  file size: %i bytes" % (metadata["filesize"]))
            if "sbxdatetime" in metadata:
                print("  SBX date&time : %s" %
                      (time.strftime("%Y-%m-%d %H:%M:%S",
                                     time.localtime(metadata["sbxdatetime"]))))
            if "filedatetime" in metadata:
                print("  file date&time: %s" %
                      (time.strftime("%Y-%m-%d %H:%M:%S",
                                     time.localtime(metadata["filedatetime"]))))
            if "hash" in metadata:
                if hashtype == 0x12:
                    print("  SHA256: %s" % (binascii.hexlify(
                        hashdigest).decode()))
                else:
                    print("hash type not recognized!")
        sys.exit(0)

    #evaluate target filename
    if not cmdline.test:
        if not filename:
            if "filename" in metadata:
                filename = metadata["filename"]
            else:
                filename = os.path.split(sbxfilename)[1] + ".out"
        elif os.path.isdir(filename):
            if "filename" in metadata:
                filename = os.path.join(filename, metadata["filename"])
            else:
                filename = os.path.join(filename,
                                        os.path.split(sbxfilename)[1] + ".out")

        if os.path.exists(filename) and not cmdline.overwrite:
            errexit(1, "target file '%s' already exists!" % (filename)) 
        print("creating file '%s'..." % (filename))
        fout= open(filename, "wb", buffering=1024*1024)

    if hashtype == 0x12:
        d = hashlib.sha256()
    lastblocknum = 0

    blockmiss = 0
    updatetime = time.time()
    blocknumber=0 
    while True:
        buffer = fin.read(sbx.blocksize)
        if len(buffer) < sbx.blocksize:
            break

        try:
            print("DATA BLOCK")
            buffer=decode_data_block_with_rsc(buffer,sbx.blocknum,sbxfilesize)

            blocknumber=blocknumber+1
            
           
            sbx.decode(buffer)

            if sbx.blocknum > lastblocknum+1:
                if cmdline.cont:
                    blockmiss += 1
                    lastblocknum += 1
                else:
                    errexit(errlev=1, mess="block %i out of order or missing"
                             % (lastblocknum+1))    
            lastblocknum += 1
            if hashcheck:
                d.update(sbx.data) 
            if not cmdline.test:
                fout.write(sbx.data)

        except seqbox.SbxDecodeError as err:
            if cmdline.cont:
                blockmiss += 1
                lastblocknum += 1
            else:
                print(err)
                errexit(errlev=1, mess="invalid block at offset %s" %
                        (hex(fin.tell()-sbx.blocksize)))

        #some progress report
        if time.time() > updatetime: 
            print("  %.1f%%" % (fin.tell()*100.0/sbxfilesize),
                  end="\r", flush=True)
            updatetime = time.time() + .1

    fin.close()
    if not cmdline.test:
        fout.close()
        if metadata:
            if "filedatetime" in metadata:
                os.utime(filename,
                         (int(time.time()), metadata["filedatetime"]))

    print("SBX decoding complete")
    if blockmiss:
        errexit(1, "missing blocks: %i" % blockmiss)

    if hashcheck:
        if hashtype == 0x12:
            print("SHA256", d.hexdigest())

        if d.digest() == hashdigest:
            print("hash match!")
        else:
            errexit(1, "hash mismatch! decoded file corrupted!")
    else:
        print("can't check integrity via hash!")
        #if filesize unknown, estimate based on 0x1a padding at block's end
        if not trimfilesize:
            c = lastEofCount(sbx.data[-4:])
            print("EOF markers at the end of last block: %i/4" % c)
    
    
def decode(sbxfilename,filename=None,password="",overwrite=False,info=False,test=False,cont=False):

    filename = sbxfilename.split(".sbx")[0]

    if not os.path.exists(sbxfilename):
        errexit(1, "sbx file '%s' not found" % (sbxfilename))
    sbxfilesize = os.path.getsize(sbxfilename)

    print("decoding '%s'..." % (sbxfilename))
    fin = open(sbxfilename, "rb", buffering=1024*1024)

    #check magic and get version
    header = fin.read(4)
    fin.seek(0, 0)
    if password:
        e = seqbox.EncDec(password, len(header))
        header= e.xor(header)
    if header[:3] != b"SBx":
        print(header[:3])
        errexit(1, "not a SeqBox file!")
    sbxver = header[3]
    
    sbx = seqbox.SbxBlock(ver=sbxver, pswd=password)
    metadata = {}
    trimfilesize = False

    hashtype = 0
    hashlen = 0
    hashdigest = b""
    hashcheck = False

    buffer = fin.read(sbx.blocksize)

    try:
        sbx.decode(buffer)
    except seqbox.SbxDecodeError as err:
        if cont == False:
            print(err)
            errexit(errlev=1, mess="invalid block at offset 0x0")

    if sbx.blocknum > 1:
        errexit(errlev=1, mess="blocks missing or out of order at offset 0x0")
    elif sbx.blocknum == 0:
        print("metadata block found!")
        metadata = sbx.metadata
        if "filesize" in metadata:
            trimfilesize = True
        if "hash" in metadata:
            hashtype = metadata["hash"][0]
            if hashtype == 0x12:
                hashlen = metadata["hash"][1]
                hashdigest = metadata["hash"][2:2+hashlen]
                hashcheck = True
        
    else:
        #first block is data, so reset from the start
        print("no metadata available")
        fin.seek(0, 0)

    #display some info and stop
    if info:
        print("\nSeqBox container info:")
        print("  file size: %i bytes" % (sbxfilesize))
        print("  blocks: %i" % (sbxfilesize / sbx.blocksize))
        print("  version: %i" % (sbx.ver))
        print("  UID: %s" % (binascii.hexlify(sbx.uid).decode()))
        if metadata:
            print("metadata:")
            if "sbxname" in metadata:
                print("  SBX name : '%s'" % (metadata["sbxname"]))
            if "filename" in metadata:
                print("  file name: '%s'" % (metadata["filename"]))
            if "filesize" in metadata:
                print("  file size: %i bytes" % (metadata["filesize"]))
            if "sbxdatetime" in metadata:
                print("  SBX date&time : %s" %
                      (time.strftime("%Y-%m-%d %H:%M:%S",
                                     time.localtime(metadata["sbxdatetime"]))))
            if "filedatetime" in metadata:
                print("  file date&time: %s" %
                      (time.strftime("%Y-%m-%d %H:%M:%S",
                                     time.localtime(metadata["filedatetime"]))))
            if "hash" in metadata:
                if hashtype == 0x12:
                    print("  SHA256: %s" % (binascii.hexlify(
                        hashdigest).decode()))
                else:
                    print("  hash type not recognized!")
        sys.exit(0)

    #evaluate target filename
    if not test:
        if not filename:
            if "filename" in metadata:
                filename = metadata["filename"]
            else:
                filename = os.path.split(sbxfilename)[1] + ".out"
        elif os.path.isdir(filename):
            if "filename" in metadata:
                filename = os.path.join(filename, metadata["filename"])
            else:
                filename = os.path.join(filename,
                                        os.path.split(sbxfilename)[1] + ".out")

        if os.path.exists(filename) and not overwrite:
            errexit(1, "target file '%s' already exists!" % (filename)) 
        print("creating file '%s'..." % (filename))
        fout= open(filename, "wb", buffering=1024*1024)

    if hashtype == 0x12:
        d = hashlib.sha256()
    lastblocknum = 0

    filesize = 0
    blockmiss = 0
    updatetime = time.time()
    redundandcy_amount=32
    rsc=RSCodec(redundandcy_amount)
    blocknumber=0 
    while True:
        buffer = fin.read(sbx.blocksize)
        if len(buffer) < sbx.blocksize:
            break

        try:

            blocknumber=blocknumber+1
            #search for first occurence of "0x1a" and cut to there
            if hex(buffer[-1])==hex(26) and (blocknumber*512+512)==sbxfilesize:
                count_of_EOF = 0
                for i in range(1,len(buffer)):
                    if hex(buffer[-i]) == hex(26):
                        count_of_EOF = count_of_EOF+1
                    else:
                        break
                rsc_decoded = rsc.decode(buffer[16:-count_of_EOF])[0]
            else:           
                rsc_decoded = rsc.decode(buffer[16:])[0]    
          
            
           
            rsc_decoded = bytes(buffer[:16])+bytes(rsc_decoded)
           
            sbx.decode(rsc_decoded)

            if sbx.blocknum > lastblocknum+1:
                if cont:
                    blockmiss += 1
                    lastblocknum += 1
                else:
                    errexit(errlev=1, mess="block %i out of order or missing"
                             % (lastblocknum+1))    
            lastblocknum += 1
            if hashcheck:
                d.update(sbx.data) 
            if not test:
                fout.write(sbx.data)

        except seqbox.SbxDecodeError as err:
            if cont:
                blockmiss += 1
                lastblocknum += 1
            else:
                print(err)
                errexit(errlev=1, mess="invalid block at offset %s" %
                        (hex(fin.tell()-sbx.blocksize)))

        #some progress report
        if time.time() > updatetime: 
            print("  %.1f%%" % (fin.tell()*100.0/sbxfilesize),
                  end="\r", flush=True)
            updatetime = time.time() + .1

    fin.close()
    if not test:
        fout.close()
        if metadata:
            if "filedatetime" in metadata:
                os.utime(filename,
                         (int(time.time()), metadata["filedatetime"]))

    print("SBX decoding complete")
    if blockmiss:
        errexit(1, "missing blocks: %i" % blockmiss)

    if hashcheck:
        if hashtype == 0x12:
            print("SHA256", d.hexdigest())

        if d.digest() == hashdigest:
            print("hash match!")
        else:
            errexit(1, "hash mismatch! decoded file corrupted!")
    else:
        print("can't check integrity via hash!")
        #if filesize unknown, estimate based on 0x1a padding at block's end
        if not trimfilesize:
            c = lastEofCount(sbx.data[-4:])
            print("EOF markers at the end of last block: %i/4" % c)


if __name__ == '__main__':
    main()
