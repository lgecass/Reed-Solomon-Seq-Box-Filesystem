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
data_size_in_bytes = 3145728
sbx_version = 2
#until here


results = []
print(results)
for k in range(1,int(data_size_in_bytes*0.0001)):    
    counts_of_failure = 0
    file_to_create = "test_file_consecutive.txt"
    print("File ", file_to_create , " created")
    f = open(file_to_create, "w")
    f.write('Y'*data_size_in_bytes)
    print("File filled with ",data_size_in_bytes ," bytes")
    f.close()
      
    Encoder.encode(file_to_create, sbx_ver= sbx_version)
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
        #position where consecutive bytes are exchanged
        position_to_tamper = random.randint(0,file_size-count_of_bytes_to_be_tampered)


        for i in range(0,count_of_bytes_to_be_tampered):
            file_sbx_encoded_copy[position_to_tamper+i] = 11



        tampered_file_name = "tampered_file_consecutive.txt.sbx"

        f = open(tampered_file_name,"wb")
        f.write(file_sbx_encoded_copy)
        f.close()
        try:
            Decoder.decode(tampered_file_name,filename="save_consecutive.txt",overwrite=True,sbx_ver=sbx_version)
        except crs.ReedSolomonError:
            counts_of_failure+=1
        except SbxDecodeError:
            counts_of_failure+=1

    results.append(counts_of_failure)
os.remove(tampered_file_name)
os.remove(file_to_create)
os.remove(encoded_file)

os.remove("save_consecutive.txt")
print(results)






    
