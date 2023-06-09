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

import sbxenc as Encoder
import sbxdec as Decoder
import random
import os
from threading import Lock
import creedsolo.creedsolo as crs
from reedsolo import ReedSolomonError
class SbxError(Exception):
    pass
class SbxDecodeError(SbxError):
    pass

#Variables you can change
run_count=10
data_size_in_bytes = 3000
sbx_version = 1
raid = True
start_procent_of_tampering = 12
end_procent_of_tampering = 13
#till here

procent_of_tampering = []

for i in range(start_procent_of_tampering,end_procent_of_tampering):
    procent_of_tampering.append(float(0.00+i/100))

results = [0] * len(procent_of_tampering)
print(results)
for k in range(0,len(procent_of_tampering)):
    print("PROCENT TAMPERING",procent_of_tampering[k])
    counts_of_failure = 0
    file_to_create = "test_file.txt"
    f = open(file_to_create, "w")
    f.write('Y'*data_size_in_bytes)
    print("File filled with ",data_size_in_bytes ," bytes")
    f.close()
      
    Encoder.encode(file_to_create, sbx_ver= sbx_version, raid=raid)
    encoded_file = file_to_create+".sbx"
    file_size = os.stat(encoded_file).st_size        
    print("File is", file_size, "bytes big")

    f = open(encoded_file, "rb")
    if raid:
        f_raid = open(encoded_file+".raid", "rb")
        raid_file = bytearray(f_raid.read())
        f_raid.close()
    
    file_sbx_encoded= bytearray(f.read())
    f.close()
    count_of_bytes_to_be_tampered = int(file_size*procent_of_tampering[k])
    print("tampered",count_of_bytes_to_be_tampered)
    for j in range(0,run_count):

        file_sbx_encoded_copy = file_sbx_encoded.copy()
        if raid:
            file_sbx_encoded_copy_raid = raid_file.copy()

        list_of_positions_to_tamper = []
        list_of_positions_to_tamper_in_raid_file = []
        for i in range (0,count_of_bytes_to_be_tampered):
            list_of_positions_to_tamper.append(random.randint(0,file_size-1))
        
        if raid:
            for i in range (0,count_of_bytes_to_be_tampered):
                list_of_positions_to_tamper_in_raid_file.append(random.randint(0,file_size-1))
        

        for i in range(0,len(list_of_positions_to_tamper)-1):
            file_sbx_encoded_copy[list_of_positions_to_tamper[i]] = 1
        
        if raid:
            for i in range(0,len(list_of_positions_to_tamper_in_raid_file)-1):
                file_sbx_encoded_copy_raid[list_of_positions_to_tamper_in_raid_file[i]] = 1
        
        tampered_file_name = "test_file.txt.sbx"

        f = open(tampered_file_name,"wb")
        f.write(file_sbx_encoded_copy)
        f.close()
        if raid:
            f_raid = open(tampered_file_name+".raid","wb")
            f_raid.write(file_sbx_encoded_copy)
            f_raid.close()
        try:
            Decoder.decode(tampered_file_name,filename="save.txt",overwrite=True,sbx_ver=sbx_version,raid=raid)
        except crs.ReedSolomonError:
            print("ERROR REED SOLOMON")
            counts_of_failure+=1
        except SbxDecodeError:
            print("ERROR SBX DECODE")
            counts_of_failure+=1

    results[k] = counts_of_failure

if os.path.exists(file_to_create):
    os.remove(file_to_create)
if os.path.exists(encoded_file):
    os.remove(encoded_file)
if os.path.exists("save.txt"):
    os.remove("save.txt")
if os.path.exists(encoded_file+".raid"):
    os.remove(encoded_file+".raid")
print(results)








    
