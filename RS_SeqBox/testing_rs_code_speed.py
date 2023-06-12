import creedsolo.creedsolo as crs
from time import time as gettime
rsc = crs.RSCodec(75)


filename = "1gb_file.txt"
sbxfilename = "1gb_filename2.txt.sbx"

fout = open(sbxfilename, "wb", buffering=1024*1024)
fin = open(filename, "rb", buffering=1024*1024)
timelist = []
while True:
        
        #buffer read is reduced to compensate added redundancy data 32 redundancy adds 64 bytes -> x*2
        buffer = fin.read(450)
        if len(buffer) == 0:
           break
       
       
        #encode buffer with rsc
        START_TIME = gettime()
        
        
        data = rsc.encode(bytearray(buffer))
        
        
        timelist.append(gettime() - START_TIME)
        fout.write(data)

sum_of_time = 0


       

print(timelist)

for time in timelist:
      sum_of_time+=time
print("total time spent:", sum_of_time)
      