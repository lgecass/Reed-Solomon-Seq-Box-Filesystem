#!/usr/bin/env python3

#--------------------------------------------------------------------------
# SeqBox - Sequenced Box container module
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
import binascii
import hashlib
import os
import random
import sys

#from reedsolo import ReedSolomonError, RSCodec
import creedsolo.creedsolo as crs

supported_vers = [1]
supported_redundancy = [1,2]

#Some custom exceptions
class SbxError(Exception):
    pass

class SbxDecodeError(SbxError):
    pass   
class SbxBlock():
    """
    Implement a basic SBX block
    """
    def __init__(self, ver=1, uid="r", redundancy=2):
        self.ver = ver
        self.padding_last_block = 0

        if ver == 1:
            self.blocksize = 512
            self.hdrsize = 16
            if redundancy == 1:
                self.redsize = 70
                self.redsym = 34
                self.padding_normal_block = 2
                self.raw_data_size_read_into_1_block = 426
            if redundancy == 2:
                self.redsize = 218
                self.redsym = 108
                self.padding_normal_block = 2
                self.raw_data_size_read_into_1_block = 278
            self.rsc_for_data_block = crs.RSCodec(self.redsym)
        if not supported_vers.__contains__(ver):
            raise SbxError("version %i not supported" % ver)
        if not supported_redundancy.__contains__(redundancy):
            raise SbxError("redundancy Level %i not supported" % redundancy)

        self.datasize = self.blocksize - self.hdrsize
        self.magic = b'SBx' + bytes([ver])
        self.blocknum = 0


        if uid == "r":
            random.seed()
            self.uid = random.getrandbits(6*8).to_bytes(6, byteorder='big')
        else:
            self.uid = (b'\x00'*6 + uid)[-6:]

        
        self.encdec = False

        self.parent_uid = 0
        self.metadata = {}
        self.data = b""

    def __str__(self):
        return "SBX Block ver: '%i', size: %i, hdr size: %i, data: %i" % \
               (self.ver, self.blocksize, self.hdrsize, self.datasize)

    def encode(self):
        if self.blocknum == 0:
            #Header Block encoding
            self.data = b""
            if "filename" in self.metadata:
                bb = self.metadata["filename"].encode()
                self.data += b"FNM" + bytes([len(bb)]) + bb
            if "sbxname" in self.metadata:
                bb = self.metadata["sbxname"].encode()
                self.data += b"SNM" + bytes([len(bb)]) + bb
            if "filesize" in self.metadata:
                bb = self.metadata["filesize"].to_bytes(8, byteorder='big')
                self.data += b"FSZ" + bytes([len(bb)]) + bb
            if "filedatetime" in self.metadata:
                bb = self.metadata["filedatetime"].to_bytes(8, byteorder='big')
                self.data += b"FDT" + bytes([len(bb)]) + bb
            if "sbxdatetime" in self.metadata:
                bb = self.metadata["sbxdatetime"].to_bytes(8, byteorder='big')
                self.data += b"SDT" + bytes([len(bb)]) + bb
            if "hash" in self.metadata:
                bb = self.metadata["hash"]
                self.data += b"HSH" + bytes([len(bb)]) + bb
            if "padding_last_block" in self.metadata:
                bb = self.metadata["padding_last_block"].to_bytes(2,byteorder="big")
                self.data += b"PAD" + bytes([len(bb)]) + bb 
            if "redundancy_level" in self.metadata:
                bb = self.metadata["redundancy_level"].to_bytes(1,byteorder="big")
                self.data += b"RSL" + bytes([len(bb)]) + bb        
            buffer = (self.uid +
                  self.blocknum.to_bytes(4, byteorder='big') +
                  self.data)
            crc = binascii.crc_hqx(buffer, self.ver).to_bytes(2,byteorder='big')
            block = self.magic + crc + buffer

            block += b'\x1A'* (self.datasize-self.redsize+self.hdrsize-len(block))
            block = self.rsc_for_data_block.encode(bytearray(block))
            block = bytes(block) + b'\x1A' * (self.blocksize - len(block))
        else: 
                buffer = (self.uid +
                  self.blocknum.to_bytes(4, byteorder='big') +
                  self.data)
                crc = binascii.crc_hqx(buffer, self.ver).to_bytes(2,byteorder='big')
                #Assemble whole 512 byte Block
                block = self.magic + crc + buffer

                block = bytes(self.rsc_for_data_block.encode(bytearray(block)))
                len_before_padding = len(block)
                block = block + b'\x1A' * (512 - len(block))
                len_after_padding = len(block)
                self.padding_last_block = len_after_padding -len_before_padding   
                
        return block

    def decode(self, buffer):
        #start setting an invalid block number
        self.blocknum = -1
        #decode eventual password
        if self.encdec:
            buffer = self.encdec.xor(buffer)
        #check the basics
        if buffer[:3] != self.magic[:3]:
            print("not an SBX block")
            #raise SbxDecodeError("not an SBX block")
        if not buffer[3] in supported_vers:
           print("block not supported")
           #raise SbxDecodeError("block v%i not supported" % buffer[3])

        self.parent_uid = 0

        self.uid = buffer[6:12]
        self.blocknum = int.from_bytes(buffer[12:16], byteorder='big')
        self.data = buffer[16:]
       

        self.metadata = {}

        if self.blocknum == 0:
            #decode meta data
            p = 0
            while p < (len(self.data)-3):
                metaid = self.data[p:p+3]
                p+=3
                if metaid[:-1] == b"\x1a\x1a":
                    break
                else:
                    metalen = self.data[p]
                    metabb = self.data[p+1:p+1+metalen]
                    p = p + 1 + metalen    
                    if metaid == b'FNM':
                        self.metadata["filename"] = metabb.decode('utf-8',errors='ignore')
                    if metaid == b'SNM':
                        self.metadata["sbxname"] = metabb.decode('utf-8',errors='ignore')
                    if metaid == b'FSZ':
                        self.metadata["filesize"] = int.from_bytes(metabb, byteorder='big')
                    if metaid == b'FDT':
                        self.metadata["filedatetime"] = int.from_bytes(metabb, byteorder='big')
                    if metaid == b'SDT':
                        self.metadata["sbxdatetime"] = int.from_bytes(metabb, byteorder='big')
                    if metaid == b'HSH':
                        self.metadata["hash"] = metabb
                    if metaid == b'PAD':
                        self.metadata["padding_last_block"] = int.from_bytes(metabb,byteorder='big')
                    if metaid == b'RSL':
                        self.metadata["redundancy_level"] = int.from_bytes(metabb,byteorder='big')
        return True

def main():
    print("SeqBox module!")
    sys.exit(0)

if __name__ == '__main__':
    main()
