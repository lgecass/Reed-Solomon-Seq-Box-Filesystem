#!/usr/bin/env python3

#--------------------------------------------------------------------------
# SBXCheck - Sequenced Box container checker - Created by Lukas Gecas
#
# Created: 21/06/2023
#
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
    parser.add_argument("-sv", "--sbxver", type=int, default=1,
                        help="SBX blocks version", metavar="n")
    res = parser.parse_args()
    return res

def get_hash_of_normal_file(path_to_file):
    """SHA256 used to verify the integrity of the encoded file"""
    with open(path_to_file, mode='rb') as fin:
        d = hashlib.sha256()
        for buf in iter(partial(fin.read, 1024*1024), b''):
            d.update(buf)
    return d.digest()

def check_whole_directory(path_to_directory, sbx_ver, recursively = False):
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
    
    print("These files need repair: ", files_needing_repair,"\n")
    print("Should they be repaired now ? Y - yes | N - No")
    input_from_user = input()
    
    if input_from_user == "y" or input_from_user == "Y" or input_from_user == "Yes" or input_from_user == "yes":
        for file in files_needing_repair:
            sbxdec.decode(file+".sbx",filename=file,sbx_ver=sbx_ver, overwrite=True)
    




def main():
    supported_sbx_versions = [1,2]
    cmdline = get_cmdline()
    if not supported_sbx_versions.__contains__(cmdline.sbxver):
        return print("sbx version not supported")
    if cmdline.folder == None:
        return print("Folder argument is necessary")
    if not cmdline.recursive:
        check_whole_directory(cmdline.folder,cmdline.sbxver)
    else:
        check_whole_directory(cmdline.folder,cmdline.sbxver, cmdline.recursive)

if __name__ == '__main__':
    main()
    