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
run_count=100
data_size_in_bytes = 3000
sbx_version = 1
raid = True
count_of_bytes_tampered_at_start = 2000
until_how_much_bytes_of_file_to_test = 2001
#until here


results = []
print(results)
for k in range(count_of_bytes_tampered_at_start,until_how_much_bytes_of_file_to_test):
    print(k," bytes to be Damaged")    
    counts_of_failure = 0
    file_to_create = "test_file_consecutive.txt"
    print("File ", file_to_create , " created")
    f = open(file_to_create, "w")
    f.write('Y'*data_size_in_bytes)
    print("File filled with ",data_size_in_bytes ," bytes")
    f.close()
      
    Encoder.encode(file_to_create, sbx_ver= sbx_version, raid=raid)
    encoded_file = file_to_create+".sbx"
    file_size = os.stat(encoded_file).st_size        
    print("File is", file_size, "bytes big")

    f = open(encoded_file, "rb")
    file_sbx_encoded= bytearray(f.read())
    f.close()

    maximal_bytes_to_change = data_size_in_bytes
    for j in range(0,run_count):
        
        count_of_bytes_to_be_tampered = k
        
        file_sbx_encoded_copy = file_sbx_encoded.copy()
        if raid:
            file_sbx_encoded_copy_raid = file_sbx_encoded.copy()
       
        #position where consecutive bytes are exchanged
        position_to_tamper = random.randint(0,file_size-count_of_bytes_to_be_tampered)
        if raid:
            position_to_tamper_raid = random.randint(0,file_size-count_of_bytes_to_be_tampered)


        for i in range(0,count_of_bytes_to_be_tampered):
            file_sbx_encoded_copy[position_to_tamper+i] = 11
        if raid:
            for i in range(0,count_of_bytes_to_be_tampered):
                file_sbx_encoded_copy_raid[position_to_tamper_raid+i] = 11

        f = open(encoded_file,"wb")
        f.write(file_sbx_encoded_copy)
        f.close()
        if raid:
            f = open(encoded_file+".raid","wb")
            f.write(file_sbx_encoded_copy_raid)
            f.close()
        try:
            Decoder.decode(encoded_file,filename="save_consecutive.txt",overwrite=True,sbx_ver=sbx_version, raid=raid)
        except crs.ReedSolomonError:
            counts_of_failure+=1
        except SbxDecodeError:
            counts_of_failure+=1

    results.append(counts_of_failure)

if os.path.exists("save_consecutive.txt"):
    os.remove("save_consecutive.txt")
if os.path.exists("test_file_consecutive.txt.sbx"):
    os.remove("test_file_consecutive.txt.sbx")
if os.path.exists("test_file_consecutive.txt.sbx.raid"):
    os.remove("test_file_consecutive.txt.sbx.raid")
if os.path.exists(file_to_create):
    os.remove(file_to_create)
if os.path.exists(encoded_file):
    os.remove(encoded_file)

print(results)






    
