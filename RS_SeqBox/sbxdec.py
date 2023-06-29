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
import time
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
    parser.add_argument("-o", "--overwrite", action="store_true", default=False,
                        help="overwrite existing file")
    parser.add_argument("-raid", "--raid", action="store_true", default=False,
                        help="Use .raid file to extend decoding capability")
    parser.add_argument("-sv", "--sbxver", type=int, default=1,
                        help="SBX blocks version", metavar="n")
    parser.add_argument("-p", "--password", type=str, default="",
                        help="decrypt with password", metavar="pass")
    res = parser.parse_args()
    return res

def errexit(errlev=1, mess=""):
    """Display an error and exit."""
    if mess != "":
        sys.stderr.write("%s: error: %s\n" %
                         (os.path.split(sys.argv[0])[1], mess))
    sys.exit(errlev)

def decode(sbxfilename,filename=None,password="",overwrite=False,info=False,test=False,cont=False,sbx_ver=1, raid=False):
    sbxfilename = sbxfilename
    filename = filename

    if os.path.isdir(sbxfilename):
        decode_whole_directory(sbxfilename)
        return
    
    if not os.path.exists(sbxfilename):
        errexit(1, "sbx file '%s' not found" % (sbxfilename))
    sbxfilesize = os.path.getsize(sbxfilename)
    
    print("decoding '%s'..." % (sbxfilename))
    fin = open(sbxfilename, "rb", buffering=1024*1024)
    raid_exists = os.path.exists(sbxfilename+".raid") and raid == True

    if raid_exists:
        fin_raid = open(sbxfilename+".raid", "rb", buffering=1024*1024)
        fin_raid.seek(0,0)
    fin.seek(0, 0)
    
    sbxver = sbx_ver
    sbx = seqbox.SbxBlock(ver=sbxver)
    metadata = {}
    
    hashtype = 0
    hashlen = 0
    hashdigest = b""
    hashcheck = False

    #read in bytes

    buffer = fin.read(sbx.blocksize)
    if raid_exists:
        buffer_raid = fin_raid.read(sbx.blocksize)
    #set symbols for reed solomon

    rsc_for_header_block = crs.RSCodec(sbx.redsym)
    #decode header with reed solomon
    try:
        buffer=bytes(rsc_for_header_block.decode(bytearray(buffer[:-sbx.padding_normal_block]))[0])
    except crs.ReedSolomonError:
        #trying Raid copy
        if raid_exists:
            try:
                buffer=bytes(rsc_for_header_block.decode(bytearray(buffer_raid[:-sbx.padding_normal_block]))[0])
            except crs.ReedSolomonError:
                pass

    sbx.decode(buffer)

    if sbx.blocknum > 1:
        return print("blocks missing or out of order")
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
        if raid_exists:
            fin_raid.seek(0,0)

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
                    print("hash type not recognized!")
            
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

    blockmiss = 0
    updatetime = time.time()
    blocknumber=0 

    #calculate hot many blocks there are in the file
    if metadata["filesize"] % sbx.raw_data_size_read_into_1_block == 0:
        count_of_blocks = metadata["filesize"] / sbx.raw_data_size_read_into_1_block
    else:
        count_of_blocks = (metadata["filesize"] - (metadata["filesize"] % sbx.raw_data_size_read_into_1_block)) / sbx.raw_data_size_read_into_1_block
    
    if password:
        encdec = seqbox.EncDec(password, sbx.raw_data_size_read_into_1_block)
    while True:
        buffer = fin.read(sbx.blocksize)
        if raid_exists:
            buffer_raid = fin_raid.read(sbx.blocksize)
            
        if len(buffer) < sbx.blocksize:
            break
        try:
            blocknumber+=1
            if raid_exists:
                try:
                    buffer = bytes(sbx.rsc_for_data_block.decode(bytearray(buffer[:-sbx.padding_normal_block]))[0])
                except crs.ReedSolomonError:
                    #trying Raid copy
                    if raid_exists:
                            buffer = bytes(sbx.rsc_for_data_block.decode(bytearray(buffer_raid[:-sbx.padding_normal_block]))[0])
            else:
                    buffer = bytes(sbx.rsc_for_data_block.decode(bytearray(buffer[:-sbx.padding_normal_block]))[0])
            
            #Decode with password if necessary
            if password:
                #only the data was encoded, so only data should be decoded
                buffer_data = encdec.xor(buffer[16:])
                buffer = buffer[:16] + buffer_data

            #LastBlock check
            if blocknumber == count_of_blocks+1:
                #cut padding
                buffer = buffer[:-metadata["padding_last_block"]]
            
                 
            sbx.decode(buffer)
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
                #errexit(errlev=1, mess="invalid block at offset %s" %
                        #(hex(fin.tell()-sbx.blocksize)))

        #some progress report
        if time.time() > updatetime: 
            print("  %.1f%%" % (fin.tell()*100.0/sbxfilesize),
                  end="\r", flush=True)
            updatetime = time.time() + .1

    fin.close()
    if raid: 
        fin_raid.close()
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

def decode_whole_directory(path_to_directory):
    sbx_files = []
    print("Decoding whole directory")  
    if os.path.exists(path_to_directory):
        if os.path.isdir(path_to_directory):
            list_of_files = []
            walk_result = []
            for result in os.walk(path_to_directory):
                walk_result= result
            for files in walk_result[2]:
                list_of_files.append(walk_result[0]+files)
            
            for file in list_of_files:
                if str(file).endswith(".sbx"):
                    sbx_files.append(file)
    for sbxfile in sbx_files:
        decode(sbxfile,sbxfile[:-4],info=False,test=False,cont=False, overwrite=True)
                     
def main():
    cmdline = get_cmdline()
    sbxfilename = cmdline.sbxfilename
    filename = cmdline.filename
    if os.path.isdir(sbxfilename):
        decode_whole_directory(sbxfilename)
        return
    
    if not os.path.exists(sbxfilename):
        errexit(1, "sbx file '%s' not found" % (sbxfilename))
    sbxfilesize = os.path.getsize(sbxfilename)
    
    print("decoding '%s'..." % (sbxfilename))
    fin = open(sbxfilename, "rb", buffering=1024*1024)
    raid_exists = os.path.exists(sbxfilename+".raid") and cmdline.raid == True

    if raid_exists:
        fin_raid = open(sbxfilename+".raid", "rb", buffering=1024*1024)
        fin_raid.seek(0,0)
    fin.seek(0, 0)
    
    sbxver = cmdline.sbxver
    sbx = seqbox.SbxBlock(ver=sbxver)
    metadata = {}
    
    hashtype = 0
    hashlen = 0
    hashdigest = b""
    hashcheck = False

    #read in bytes

    buffer = fin.read(sbx.blocksize)
    if raid_exists:
        buffer_raid = fin_raid.read(sbx.blocksize)
    #set symbols for reed solomon

    rsc_for_header_block = crs.RSCodec(sbx.redsym)
    #decode header with reed solomon
    try:
        buffer=bytes(rsc_for_header_block.decode(bytearray(buffer[:-sbx.padding_normal_block]))[0])
    except crs.ReedSolomonError:
        #trying Raid copy
        if raid_exists:
            try:
                buffer=bytes(rsc_for_header_block.decode(bytearray(buffer_raid[:-sbx.padding_normal_block]))[0])
            except crs.ReedSolomonError:
                pass

    sbx.decode(buffer)

    if sbx.blocknum > 1:
        return print("blocks missing or out of order")
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
        if raid_exists:
            fin_raid.seek(0,0)

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

    #calculate hot many blocks there are in the file
    if metadata["filesize"] % sbx.raw_data_size_read_into_1_block == 0:
        count_of_blocks = metadata["filesize"] / sbx.raw_data_size_read_into_1_block
    else:
        count_of_blocks = (metadata["filesize"] - (metadata["filesize"] % sbx.raw_data_size_read_into_1_block)) / sbx.raw_data_size_read_into_1_block
    
    if cmdline.password:
        encdec = seqbox.EncDec(cmdline.password, sbx.raw_data_size_read_into_1_block)
    while True:
        buffer = fin.read(sbx.blocksize)
        if raid_exists:
            buffer_raid = fin_raid.read(sbx.blocksize)
            
        if len(buffer) < sbx.blocksize:
            break
        try:
            blocknumber+=1
            if raid_exists:
                try:
                    buffer = bytes(sbx.rsc_for_data_block.decode(bytearray(buffer[:-sbx.padding_normal_block]))[0])
                except crs.ReedSolomonError:
                    #trying Raid copy
                    if raid_exists:
                            buffer = bytes(sbx.rsc_for_data_block.decode(bytearray(buffer_raid[:-sbx.padding_normal_block]))[0])
            else:
                    buffer = bytes(sbx.rsc_for_data_block.decode(bytearray(buffer[:-sbx.padding_normal_block]))[0])
            #Decode with password if necessary
            if cmdline.password:
                #only the data was encoded, so only data should be decoded
                buffer_data = encdec.xor(buffer[16:])
                buffer = buffer[:16] + buffer_data
            #LastBlock check
            if blocknumber == count_of_blocks+1:
                #cut padding
                buffer = buffer[:-metadata["padding_last_block"]]
            
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
                #errexit(errlev=1, mess="invalid block at offset %s" %
                        #(hex(fin.tell()-sbx.blocksize)))

        #some progress report
        if time.time() > updatetime: 
            print("  %.1f%%" % (fin.tell()*100.0/sbxfilesize),
                  end="\r", flush=True)
            updatetime = time.time() + .1

    fin.close()
    if cmdline.raid: 
        fin_raid.close()
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
   
            
if __name__ == '__main__':
    main()
