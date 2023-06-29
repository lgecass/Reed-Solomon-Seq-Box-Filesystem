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
#----------------------------------------------------------------------------------

import creedsolo.creedsolo as crs
import os
import argparse
import hashlib
from functools import partial

try:
    import RS_SeqBox.seqbox as seqbox
except ImportError:
    pass
try:
    import seqbox as seqbox
except ImportError:
    pass
try:
    import RS_SeqBox.sbxenc as sbxenc
except ImportError:
    pass
try:
    import sbxdec as sbxdec
except ImportError:
    pass
try:
    import RS_SeqBox.sbxdec as sbxdec
except ImportError:
    pass

PROGRAM_VER = "1.0.2"

def decode_header_block_with_rsc(buffer, sbx_version):
    sbx = seqbox.SbxBlock(ver=sbx_version)
    rsc=crs.RSCodec(sbx.redsym)
    decoded = bytes(rsc.decode(bytearray(buffer[:-sbx.padding_normal_block]))[0])
    return decoded

def get_hash_of_sbx_file(path_to_file, sbx_version):
    if not os.path.exists(path_to_file):
        print(1, "sbx file '%s' not found" % (path_to_file))
        return
    
    sbx = seqbox.SbxBlock(ver=sbx_version)
    fin = open(path_to_file, "rb", buffering=1024*1024)
    
    buffer = fin.read(sbx.blocksize)

    buffer = bytes(decode_header_block_with_rsc(buffer, sbx_version))

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
    
def get_cmdline():
    """Evaluate command line parameters, usage & help."""
    parser = argparse.ArgumentParser(
             description="decode a SeqBox container",
             formatter_class=argparse.ArgumentDefaultsHelpFormatter,
             prefix_chars='-+')
    parser.add_argument("-v", "--version", action='version', 
                        version='SeqBox - Sequenced Box container - ' +
                        'Decoder v%s - (C) 2017 by M.Pontello' % PROGRAM_VER) 
    parser.add_argument("folder", action="store", nargs='?', 
                        help="Folder to check")
    parser.add_argument("-r", "--recursive", action="store_true", default=False,
                        help="Check recursively through folders")
    parser.add_argument("-o", "--overwrite", action="store_true", default=False,
                        help="overwrite existing file")
    parser.add_argument("-raid", "--raid", action="store_true", default=False,
                        help="use existing raid files for recovery")
    parser.add_argument("-auto", "--auto", action="store_true", default=False,
                        help="Automatically repair without asking")
    parser.add_argument("-sv", "--sbxver", type=int, default=1,
                        help="SBX blocks version", metavar="n")
    parser.add_argument("-p", "--password", type=str, default="",
                        help="decrypt with password if password used", metavar="pass")
    res = parser.parse_args()
    return res

def get_hash_of_normal_file(path_to_file):
    """SHA256 used to verify the integrity of the encoded file"""
    with open(path_to_file, mode='rb') as fin:
        d = hashlib.sha256()
        for buf in iter(partial(fin.read, 1024*1024), b''):
            d.update(buf)
    return d.digest()

def check_whole_directory(path_to_directory, sbx_ver, recursively = False, raid = False, password="", auto=False):
    if not os.path.exists(path_to_directory) or not os.path.isdir(path_to_directory):
        print("directory does not exist or is not a directory")
        return
    
    list_of_files = []
    files_to_check = []
    walk_result = []
    files_needing_repair = []
    for result in os.walk(path_to_directory):
        walk_result.append(result)
    ## Walk returns [(Folder),(folders inside this folder), (files_inside_folder)], [...]

    if not recursively:
        for file in walk_result[0][2]:
            list_of_files.append(walk_result[0][0] +"/"+ file)
    else:
        for directory_info in walk_result:
            for file in directory_info[2]:
                list_of_files.append(directory_info[0] +"/"+ file)

    if len(list_of_files) == 0:
        return print("Directory is empty") 
            
    for file in list_of_files:
        if not str(file).endswith(".sbx") and os.path.exists(file+".sbx"):
            files_to_check.append(file)
        
    for file in files_to_check:
        
        hash_of_file = get_hash_of_normal_file(file)
        hash_inside_sbx_file = get_hash_of_sbx_file(file+".sbx", sbx_version=sbx_ver)
        
        if hash_of_file != hash_inside_sbx_file:
            files_needing_repair.append(file)
    
    if len(files_needing_repair) == 0:
        return print("All Files are correct, no need to repair")
    if not auto:
        print("These files need repair: ", files_needing_repair,"\n")
        print("Should they be repaired now ? Y - yes | N - No")
        input_from_user = input()
        
        if input_from_user == "y" or input_from_user == "Y" or input_from_user == "Yes" or input_from_user == "yes":
            for file in files_needing_repair:
                sbxdec.decode(file+".sbx",filename=file,sbx_ver=sbx_ver, overwrite=True,raid=raid)
    else:
        for file in files_needing_repair:
            sbxdec.decode(file+".sbx",filename=file,sbx_ver=sbx_ver, overwrite=True,raid=raid,password=password)
    
def main():
    supported_sbx_versions = [1,2]
    cmdline = get_cmdline()
    if not supported_sbx_versions.__contains__(cmdline.sbxver):
        return print("sbx version not supported")
    if cmdline.folder == None:
        return print("Folder argument is necessary")
    if not cmdline.recursive:
        
        check_whole_directory(cmdline.folder,cmdline.sbxver,raid=cmdline.raid,password=cmdline.password)
    else:
        check_whole_directory(cmdline.folder,cmdline.sbxver, cmdline.recursive,raid=cmdline.raid,password=cmdline.password)
def check(folder,sbxver=1,recursive=False,raid=False,password="",auto=False):
    supported_sbx_versions = [1,2]

    if not supported_sbx_versions.__contains__(sbxver):
        return print("sbx version not supported")
    if folder == None:
        return print("Folder argument is necessary")
    if not recursive:
        
        check_whole_directory(folder,sbxver,raid=raid,password=password,auto=auto)
    else:
        check_whole_directory(folder,sbxver, recursive,raid=raid,password=password, auto=auto)



if __name__ == '__main__':
    main()
    