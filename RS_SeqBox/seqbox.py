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
import binascii
import hashlib
import os
import random
import sys

#from reedsolo import ReedSolomonError, RSCodec
import creedsolo.creedsolo as crs

supported_vers = [1,2]

#Some custom exceptions
class SbxError(Exception):
    pass

class SbxDecodeError(SbxError):
    pass   
class SbxBlock():
    """
    Implement a basic SBX block
    """
    def __init__(self, ver=1, uid="r",pswd=""):
        self.ver = ver
        self.padding_last_block = 0

        if ver == 1:
            self.blocksize = 512 #Total Block size
            self.hdrsize = 16 #Header size
            self.redsize = 218 #How much redundancy data is added
            self.redsym = 108 #How many ECC symbols are used
            self.padding_normal_block = 2 #What Padding occurs at the end of normal blocks
            self.raw_data_size_read_into_1_block = 278 #How many bytes can be read from the file
            self.rsc_for_data_block = crs.RSCodec(self.redsym) #rsc means Reed-Solomon_Code
        if ver == 2:
            self.blocksize = 4096 
            self.hdrsize = 16
            self.redsize = 1728
            self.redsym = 107
            self.padding_normal_block = 16
            self.raw_data_size_read_into_1_block = 2352
            self.rsc_for_data_block = crs.RSCodec(self.redsym)
            
        if not supported_vers.__contains__(ver):
            raise SbxError("version %i not supported" % ver)

        self.datasize = self.blocksize - self.hdrsize
        self.magic = b'SBx' + bytes([ver])
        self.blocknum = 0

        if uid == "r":
            random.seed()
            self.uid = random.getrandbits(6*8).to_bytes(6, byteorder='big')
        else:
            self.uid = (b'\x00'*6 + uid)[-6:]

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
                buffer = (self.uid + self.blocknum.to_bytes(4, byteorder='big') + self.data)
                crc = binascii.crc_hqx(buffer, self.ver).to_bytes(2,byteorder='big')
                #Assemble whole Block
                block = self.magic + crc + buffer
                block = bytes(self.rsc_for_data_block.encode(bytearray(block)))
            
                len_before_padding = len(block)
                block = block + b'\x1A' * (self.blocksize - len(block))
                len_after_padding = len(block)
                self.padding_last_block = len_after_padding -len_before_padding   
        return block

    def decode(self, buffer):
        #start setting an invalid block number
        self.blocknum = -1

        #check the basics
        if buffer[:3] != self.magic[:3]:
            print("not an SBX block")
        if not buffer[3] in supported_vers:
           print("block not supported")     

        self.uid = buffer[6:12]
        self.blocknum = int.from_bytes(buffer[12:16], byteorder='big')
        self.data = buffer[16:]
        self.parent_uid = 0

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
class EncDec():
    """Simple encoding/decoding function"""
    #it's not meant as 'strong encryption', but just to hide the presence
    #of SBX blocks on a simple scan
    def __init__(self, key, size):
        #key is kept as a bigint because a xor between two bigint is faster
        #than byte-by-byte
        d = hashlib.sha256()
        key = key.encode()
        tempkey = key
        while len(tempkey) < size:
            d.update(tempkey)
            key = d.digest()
            tempkey += key
        self.key = int(binascii.hexlify(tempkey[:size]), 16)
    def xor(self, buffer):
        num = int(binascii.hexlify(buffer), 16) ^ self.key
        return binascii.unhexlify(hex(num)[2:])
def main():
    print("SeqBox module!")
    sys.exit(0)

if __name__ == '__main__':
    main()
