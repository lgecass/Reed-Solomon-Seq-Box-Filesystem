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
import sqlite3
import time

import seqbox

PROGRAM_VER = "1.0.2"

def get_cmdline():
    """Evaluate command line parameters, usage & help."""
    parser = argparse.ArgumentParser(
             description="recover SeqBox containers",
             formatter_class=argparse.ArgumentDefaultsHelpFormatter,
             prefix_chars='-+',
             fromfile_prefix_chars='@')
    parser.add_argument("-v", "--version", action='version', 
                        version='SeqBox - Sequenced Box container - ' +
                        'Recover v%s - (C) 2017 by M.Pontello' % PROGRAM_VER) 
    parser.add_argument("dbfilename", action="store", metavar="filename",
                        help="database with recovery info")
    parser.add_argument("destpath", action="store", nargs="?", metavar="path",
                        help="destination path for recovered sbx files")
    parser.add_argument("--all", action="store_true", help="recover all")
    parser.add_argument("--file", action="store", nargs="+", metavar="filename",
                        help="original filename(s) to recover")
    parser.add_argument("--sbx", action="store", nargs="+", metavar="filename",
                        help="SBX filename(s) to recover")
    parser.add_argument("--uid", action="store", nargs="+", metavar="uid",
                        help="UID(s) to recover")
    parser.add_argument("-f", "--fill", action="store_true", default=False,
                        help="fill-in missing blocks")
    parser.add_argument("-i", "--info", action="store_true", default=False,
                        help="show info on recoverable sbx file(s)")
    parser.add_argument("-p", "--password", type=str, default="",
                        help="encrypt with password", metavar="pass")
    parser.add_argument("-o", "--overwrite", action="store_true", default=False,
                        help="overwrite existing sbx file(s)")
    res = parser.parse_args()
    return res


def errexit(errlev=1, mess=""):
    """Display an error and exit."""
    if mess != "":
        sys.stderr.write("%s: error: %s\n" %
                         (os.path.split(sys.argv[0])[1], mess))
    sys.exit(errlev)


class RecDB():
    """Helper class to access Sqlite3 DB with recovery info"""

    def __init__(self, dbfilename):
        self.connection = sqlite3.connect(dbfilename)
        self.cursor = self.connection.cursor()

    def GetMetaFromUID(self, uid):
        meta = {}
        c = self.cursor
        c.execute("SELECT * from sbx_meta where uid = '%i'" % uid)
        res = c.fetchone()
        if res:
            meta["filesize"] = res[1]
            meta["filename"] = res[2]
            meta["sbxname"] = res[3]
            meta["filedatetime"] = res[4]
            meta["sbxdatetime"] = res[5]
        return meta

    def GetUIDFromFileName(self, filename):
        c = self.cursor
        c.execute("select uid from sbx_meta where name = '%s'" % (filename))
        res = c.fetchone()
        if res:
            return(res[0])

    def GetUIDFromSbxName(self, sbxname):
        c = self.cursor
        c.execute("select uid from sbx_meta where sbxname = '%s'" % (sbxname))
        res = c.fetchone()
        if res:
            return(res[0])

    def GetBlocksCountFromUID(self, uid):
        c = self.cursor
        c.execute("SELECT uid from sbx_blocks where uid = '%i' group by num order by num" % (uid))
        return len(c.fetchall())

    def GetBlocksListFromUID(self, uid):
        c = self.cursor
        c.execute("SELECT num, fileid, pos from sbx_blocks where uid = '%i' group by num order by num" % (uid))
        return c.fetchall()

    def GetUIDDataList(self):
        c = self.cursor
        c.execute("SELECT * from sbx_uids")
        res = {row[0]:row[1] for row in c.fetchall()}
        return res

    def GetSourcesList(self):
        c = self.cursor
        c.execute("SELECT * FROM sbx_source")
        return c.fetchall()


def uniquifyFileName(filename):
    count = 0
    uniq = ""
    name,ext = os.path.splitext(filename)
    while os.path.exists(filename):
        count += 1
        uniq = "(%i)" % count
        filename = name + uniq + ext
    return filename


def report(db, uidDataList, blocksizes):
    """Create a report with the info obtained by SbxScan"""
    #just the basic info in CSV format for the moment

    print('\n"UID", "filesize", "sbxname", "filename", "filedatetime"')

    for uid in uidDataList:
        hexdigits = binascii.hexlify(uid.to_bytes(6, byteorder="big")).decode()
        metadata = db.GetMetaFromUID(uid)
        blocksnum = db.GetBlocksCountFromUID(uid)
        filename = metadata["filename"] if "filename" in metadata else ""
        sbxname = metadata["sbxname"] if "sbxname" in metadata else ""
        if "filesize" in metadata:
            filesize = metadata["filesize"]
        else:
            filesize = blocksnum * blocksizes[uidDataList[uid]]
        filedatetime = "n/a"
        if "filedatetime" in metadata:
            if metadata["filedatetime"] >= 0:
                filedatetime = time.strftime("%Y-%m-%d %H:%M:%S",
                                     time.localtime(metadata["filedatetime"]))
        
        print('"%s", %i, "%s", "%s", "%s"' %
              (hexdigits, filesize, sbxname, filename, filedatetime))


def report_err(db, uiderrlist, uidDataList, blocksizes):
    """Create a report with recovery errors"""
    #just the basic info in CSV format for the moment

    print('\n"UID", "blocks", "errs", "filesize", "sbxname", "filename"')
    for info in uiderrlist:
        uid = info[0]
        errblocks = info[1]
        hexdigits = binascii.hexlify(uid.to_bytes(6, byteorder="big")).decode()
        metadata = db.GetMetaFromUID(uid)
        blocksnum = db.GetBlocksCountFromUID(uid)
        filename = metadata["filename"] if "filename" in metadata else ""
        sbxname = metadata["sbxname"] if "sbxname" in metadata else ""

        if "filesize" in metadata:
            filesize = metadata["filesize"]
        else:
            filesize = blocksnum * blocksizes[uidDataList[uid]]
        
        print('"%s", %i, %i, %i, "%s", "%s"' %
              (hexdigits, blocksnum, errblocks, filesize, sbxname, filename))


def main():

    cmdline = get_cmdline()

    dbfilename = cmdline.dbfilename
    if not os.path.exists(dbfilename) or os.path.isdir(dbfilename):
        errexit(1,"file '%s' not found!" % (dbfilename))

    #open database
    print("opening '%s' recovery info database..." % (dbfilename))
    db = RecDB(dbfilename)

    #get data on all uids present
    uidDataList = db.GetUIDDataList()

    #get blocksizes for every supported SBx version
    blocksizes = {}
    for v in seqbox.supported_vers:
        blocksizes[v] = seqbox.SbxBlock(ver=v).blocksize
    
    #info/report
    if cmdline.info:
        report(db, uidDataList, blocksizes)
        errexit(0)

    #build a list of uids to recover:
    uidRecoList = []
    if cmdline.all:
        uidRecoList = list(uidDataList)
    else:
        if cmdline.uid:
            for hexuid in cmdline.uid:
                if len(hexuid) % 2 != 0:
                    errexit(1, "invalid UID!")
                uid = int.from_bytes(binascii.unhexlify(hexuid),
                                     byteorder="big")
                if db.GetBlocksCountFromUID(uid):
                    uidRecoList.append(uid)
                else:
                    errexit(1,"no recoverable UID '%s'" % (hexuid))
        if cmdline.sbx:
            for sbxname in cmdline.sbx:
                uid = db.GetUIDFromSbxName(sbxname)
                if uid:
                    uidRecoList.append(uid)
                else:
                    errexit(1,"no recoverable sbx file '%s'" % (sbxname))
        if cmdline.file:
            for filename in cmdline.file:
                uid = db.GetUIDFromFileName(filename)
                if uid:
                    uidRecoList.append(uid)
                else:
                    errexit(1,"no recoverable file '%s'" % (filename))

    if len(uidRecoList) == 0:
        errexit(1, "nothing to recover!")

    print("recovering SBX files...")
    uid_list = sorted(set(uidRecoList))

    #open all the sources
    finlist = {}
    for key, value in db.GetSourcesList():
        finlist[key] = open(value, "rb")

    uidcount = 0
    totblocks = 0
    totblockserr = 0
    uiderrlist = []
    for uid in uidRecoList:
        uidcount += 1
        sbxver = uidDataList[uid]
        sbx = seqbox.SbxBlock(ver=sbxver)
        hexuid = binascii.hexlify(uid.to_bytes(6, byteorder="big")).decode()
        print("UID %s (%i/%i)" % (hexuid, uidcount, len(uid_list)))

        blocksnum = db.GetBlocksCountFromUID(uid)
        print("  blocks: %i - size: %i bytes" %
              (blocksnum, blocksnum * sbx.blocksize))
        meta = db.GetMetaFromUID(uid)
        if "sbxname" in meta:
            sbxname = meta["sbxname"]
        else:
            #use hex uid as name if no metadata present
            sbxname = (binascii.hexlify(uid.to_bytes(6, byteorder="big")).decode() +
                       ".sbx")
        if cmdline.destpath:
            sbxname = os.path.join(cmdline.destpath, sbxname)
        print("  to: '%s'" % sbxname)

        if not cmdline.overwrite:
            sbxname = uniquifyFileName(sbxname)
        fout = open(sbxname, "wb", buffering = 1024*1024)

        blockdatalist = db.GetBlocksListFromUID(uid)
        #read 1 block to initialize the correct block parameters
        #(needed for filling in missing blocks)
        blockdata = blockdatalist[0]
        fin = finlist[blockdata[1]]
        bpos = blockdata[2]
        fin.seek(bpos, 0)
        try:
            sbx.decode(fin.read(sbx.blocksize))
        except seqbox.SbxDecodeError as err:
            print(err)
            errexit(1, "invalid block at offset %s file '%s'" %
                    (hex(bpos), fin.name))
        
        lastblock = -1
        ticks = 0
        missingblocks = 0
        updatetime = time.time() -1
        maxbnum =  blockdatalist[-1][0]
        #loop trough the block list and recreate SBx file
        for blockdata in blockdatalist:
            bnum = blockdata[0]
            #check for missing blocks and fill in
            if bnum != lastblock +1 and bnum != 1:
                for b in range(lastblock+1, bnum):
                    #no point in an empty block 0 with no metadata
                    if b > 0 and cmdline.fill:
                        sbx.blocknum = b
                        sbx.data = bytes(sbx.datasize)
                        buffer = sbx.encode(sbx)
                        fout.write(buffer)
                    missingblocks += 1

            fin = finlist[blockdata[1]]
            bpos = blockdata[2]
            fin.seek(bpos, 0)
            buffer = fin.read(sbx.blocksize)
            fout.write(buffer)
            lastblock = bnum

            #some progress report
            #if time.time() > updatetime or bnum == maxbnum:
                #print("  %.1f%%" % (bnum*100.0/maxbnum), " ",
                      #"(missing blocks: %i)" % missingblocks,
                     # end="\r", flush=True)
                #updatetime = time.time() + .5

        fout.close()
        #set sbx date&time
        if "sbxdatetime" in meta:
            if meta["sbxdatetime"] >= 0:
                os.utime(sbxname, (int(time.time()), meta["sbxdatetime"]))
        
        print()
        if missingblocks > 0:
            uiderrlist.append((uid, missingblocks))
            totblockserr += missingblocks

    print("\ndone.")
    if len(uiderrlist) == 0:
        print("all SBx files recovered with no errors!")
    else:
        print("errors detected in %i SBx file(s)!" % len(uiderrlist))
        report_err(db, uiderrlist, uidDataList, blocksizes)

            
if __name__ == '__main__':
    main()
