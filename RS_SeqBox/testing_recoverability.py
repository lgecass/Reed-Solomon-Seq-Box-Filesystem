import sbxenc as Encoder
import sbxdec as Decoder
import random
import os
from threading import Lock
from reedsolo import ReedSolomonError
class SbxError(Exception):
    pass
class SbxDecodeError(SbxError):
    pass

run_count=100
data_size_in_bytes = 30000
lock = Lock()
threads = list()
procent_of_tampering = [0.01,0.02,0.03,0.04,0.05,0.06,0.07,0.08,0.09,0.1,0.11,0.12,0.13,0.14,0.15,0.17,0.18,0.19,0.20,0.21,0.22,0.23,0.24,0.26,0.27,0.28,0.29,0.30,0.31,0.32]
results = [0] * len(procent_of_tampering)
print(results)
for k in range(0,len(procent_of_tampering)):
    
    counts_of_failure = 0
    file_to_create = "test_file.txt"
    print("File ", file_to_create , " created")
    f = open(file_to_create, "w")
    f.write('Y'*data_size_in_bytes)
    print("File filled with ",data_size_in_bytes ," bytes")
    f.close()
      
    Encoder.encode(file_to_create)
    encoded_file = file_to_create+".sbx"
    file_size = os.stat(encoded_file).st_size        
    print("File is", file_size, "bytes big")

    f = open(encoded_file, "rb")

    file_sbx_encoded= bytearray(f.read())
    f.close()
    count_of_bytes_to_be_tampered = int(file_size*procent_of_tampering[k])
    for j in range(0,run_count):

        file_sbx_encoded_copy = file_sbx_encoded.copy()
        list_of_positions_to_tamper = []
        for i in range (0,count_of_bytes_to_be_tampered):
            list_of_positions_to_tamper.append(random.randint(0,file_size-1))

        for i in range(0,len(list_of_positions_to_tamper)-1):
            file_sbx_encoded_copy[list_of_positions_to_tamper[i]] = 1


        tampered_file_name = "tampered_file.txt.sbx"

        f = open(tampered_file_name,"wb")
        f.write(file_sbx_encoded_copy)
        f.close()
        try:
            Decoder.decode(tampered_file_name,filename="save.txt",overwrite=True)
        except ReedSolomonError:
            print("ERROR REED SOLOMON")
            counts_of_failure+=1
            
        except SbxDecodeError:
            print("ERROR SBX DECODE")
            counts_of_failure+=1
    print(k)
    results[k] = counts_of_failure
os.remove(tampered_file_name)
os.remove(file_to_create)
os.remove(encoded_file)
os.remove("save.txt")


print(results)




    
