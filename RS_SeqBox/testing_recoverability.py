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
run_count=1
data_size_in_bytes = 41943
sbx_version = 1
raid = False
#till here

#procent_of_tampering = [0.01,0.02,0.03,0.04,0.05,0.06,0.07,0.08,0.09,0.1,0.11,0.12,0.13,0.14,0.15,0.17,0.18,0.19,0.20,0.21,0.22,0.23,0.24,0.26,0.27,0.28,0.29,0.30,0.31,0.32,0.33,0.34,0.35,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,0.32,]
procent_of_tampering = []
for i in range(0,200):
    procent_of_tampering.append(float(0.00+i/100))
print(procent_of_tampering)
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
#os.remove(tampered_file_name)
os.remove(file_to_create)
os.remove(encoded_file)
print(results)
os.remove("save.txt")







    
