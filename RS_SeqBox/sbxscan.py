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

import os
import sys
import argparse
import binascii
from time import sleep, time
import sqlite3
import creedsolo.creedsolo as crs
import seqbox
from collections.abc import Sequence, Mapping
PROGRAM_VER = "1.0.1"

def decode_data_block(buffer, sbx):
    redundancy=sbx.redsym 
    rsc=crs.RSCodec(redundancy)
    buffer = bytes(rsc.decode(bytearray(buffer[:-sbx.padding_normal_block]))[0])   
    return buffer 


def get_cmdline():
    """Evaluate command line parameters, usage & help."""
    parser = argparse.ArgumentParser(
             description=("scan files/devices for SBx blocks and create a "+
                          "detailed report plus an index to be used with "+
                          "SBXScan"),
             formatter_class=argparse.ArgumentDefaultsHelpFormatter,
             prefix_chars='-', fromfile_prefix_chars='@')
    parser.add_argument("-v", "--version", action='version', 
                        version='SeqBox - Sequenced Box container - ' +
                        'Scanner v%s - (C) 2017 by M.Pontello' % PROGRAM_VER) 
    parser.add_argument("filename", action="store", nargs="+",
                        help="file(s) to scan")
    parser.add_argument("-d", "--database", action="store", dest="dbfilename",
                        metavar="filename",
                        help="where to save recovery info",
                        default="sbxscan.db3")
    parser.add_argument("-o", "--offset", type=int, default=0,
                        help=("offset from the start"), metavar="n")
    parser.add_argument("-st", "--step", type=int, default=0,
                        help=("scan step"), metavar="n")
    parser.add_argument("-b", "--buffer", type=int, default=1024,
                        help=("read buffer in KB"), metavar="n")
    parser.add_argument("-sv", "--sbxver", type=int, default=1,
                        help="SBX blocks version to search for", metavar="n")
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

      
def getFileSize(filename):
    """Calc file size - works on devices too"""
    ftemp = os.open(filename, os.O_RDONLY)
    try:
        return os.lseek(ftemp, 0, os.SEEK_END)
    finally:
        os.close(ftemp)


def main():

    cmdline = get_cmdline()

    filenames = []
    for filename in cmdline.filename:
        if os.path.exists(filename):
            filenames.append(filename)
        else:
            errexit(1, "file '%s' not found!" % (filename))
    filenames = sorted(set(filenames), key=os.path.getsize)

    dbfilename = cmdline.dbfilename
    if os.path.isdir(dbfilename):
        dbfilename = os.path.join(dbfilename, "sbxscan.db3")

    #create database tables
    print("creating '%s' database..." % (dbfilename))
    if os.path.exists(dbfilename):
        os.remove(dbfilename)
    conn = sqlite3.connect(dbfilename)
    c = conn.cursor()
    c.execute("CREATE TABLE sbx_source (id INTEGER, name TEXT)")
    c.execute("CREATE TABLE sbx_meta (uid INTEGER, size INTEGER, name TEXT, sbxname TEXT, datetime INTEGER, sbxdatetime INTEGER, fileid INTEGER)")
    c.execute("CREATE TABLE sbx_uids (uid INTEGER, ver INTEGER)")
    c.execute("CREATE TABLE sbx_blocks (uid INTEGER, num INTEGER, fileid INTEGER, pos INTEGER )")
    c.execute("CREATE INDEX blocks ON sbx_blocks (uid, num, pos)")

    #scan all the files/devices
    sbx = seqbox.SbxBlock(ver=cmdline.sbxver)
    offset = cmdline.offset
    filenum = 0
    uids = {}
    magic = b'SBx' + bytes([cmdline.sbxver])
    if cmdline.password:
        magic = seqbox.EncDec(cmdline.password, len(magic)).xor(magic)
    scanstep = cmdline.step
    if scanstep == 0:
        scanstep = sbx.blocksize

    for filename in filenames:
        filenum += 1
        print("scanning file/device '%s' (%i/%i)..." %
              (filename, filenum, len(filenames)))
        filesize = getFileSize(filename)

        c.execute("INSERT INTO sbx_source (id, name) VALUES (?, ?)",
          (filenum, filename))
        conn.commit()

        fin = open(filename, "rb", buffering=cmdline.buffer*1024)
        blocksfound = 0
        blocksmetafound = 0
        updatetime = time() - 1
        starttime = time()
        docommit = False
        for pos in range(offset, filesize, scanstep):
            fin.seek(pos, 0)
            buffer = fin.read(sbx.blocksize)
            try:
                #decode with reed solomon
                buffer = decode_data_block(buffer, sbx)
            except crs.ReedSolomonError:
                #not a sbx block or too many errors
                pass
            #check for magic
            if buffer[:4] == magic:
                #check for valid block
                try:
                    sbx.decode(buffer)
                    #update uids table & list
                    if not sbx.uid in uids:
                        uids[sbx.uid] = True
                        c.execute(
                                "INSERT INTO sbx_uids (uid, ver) VALUES (?, ?)",
                                (int.from_bytes(sbx.uid, byteorder='big'),
                                sbx.ver))
                        docommit = True

                    #update blocks table
                    blocksfound+=1
                    c.execute(
                        "INSERT INTO sbx_blocks (uid, num, fileid, pos) VALUES (?, ?, ?, ?)",
                            (int.from_bytes(sbx.uid, byteorder='big'),
                            sbx.blocknum, filenum, pos))
                    docommit = True
                    
                        #update meta table
                    if sbx.blocknum == 0:
                        blocksmetafound += 1
                        if not "filedatetime" in sbx.metadata:
                            sbx.metadata["filedatetime"] = -1
                            sbx.metadata["sbxdatetime"] = -1

                        c.execute(
                                "INSERT INTO sbx_meta (uid , size, name, sbxname, datetime, sbxdatetime, fileid) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                (int.from_bytes(sbx.uid, byteorder='big'),
                                sbx.metadata["filesize"],
                                sbx.metadata["filename"], sbx.metadata["sbxname"],
                                sbx.metadata["filedatetime"], sbx.metadata["sbxdatetime"],
                                filenum))
                        docommit = True

                except seqbox.SbxDecodeError and KeyError:
                    # print("error")
                    pass

            #status update
            if (time() > updatetime) or (pos >= filesize - scanstep):
                etime = (time()-starttime)
                if etime == 0:
                    etime = 1
                print("%5.1f%% blocks: %i - meta: %i - files: %i - %.2fMB/s" %
                      (pos*100.0/(filesize-scanstep), blocksfound,
                       blocksmetafound, len(uids), pos/(1024*1024)/etime),
                      end = "\r", flush=True)
                if docommit:
                    conn.commit()
                    docommit = False
                updatetime = time() + .5
            
        fin.close()
        print()

    c.close()
    conn.close()

    print("scan completed!")    


if __name__ == '__main__':
    main()
