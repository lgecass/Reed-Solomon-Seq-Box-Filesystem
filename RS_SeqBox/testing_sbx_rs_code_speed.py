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
from time import time as gettime
import os

file_size_to_encode = 1000# bytes
repetitions = 1
sbxversion = 1
raid = True
filename = "file_to_test.txt"

f = open(filename, "w")
if not os.path.exists(filename):
      exit("File does not exist")

f.write('Y'*file_size_to_encode)
f.close()

time_list_encoding = []
time_list_decoding = [] 

#encode buffer with rsc
for i in range(0,repetitions):

      START_TIME_ENCODING = gettime()
      Encoder.encode(filename,sbx_ver=sbxversion, raid=raid)
      TIME_AFTER_ENCODING = gettime() 

      encoding_time = TIME_AFTER_ENCODING - START_TIME_ENCODING
      print("Encoding time for ",str(file_size_to_encode)," bytes:",(encoding_time),"s")

      time_list_encoding.append(encoding_time)
      
      START_TIME_DECODING = gettime()
      Decoder.decode(filename+".sbx", overwrite= True,sbx_ver=sbxversion,raid=raid)
      TIME_AFTER_DECODING = gettime() 

      decoding_time = TIME_AFTER_DECODING - START_TIME_DECODING
      print("Decoding time for ",str(os.lstat(filename+".sbx").st_size)," bytes:",(decoding_time),"s")

      time_list_decoding.append(decoding_time)

sum_of_encoding_times = 0
sum_of_decoding_times = 0
for time in time_list_encoding:
      sum_of_encoding_times += time

for time in time_list_decoding:
      sum_of_decoding_times+=time

if repetitions != 0:
      average_time_encoding = sum_of_encoding_times / repetitions
      average_time_decoding = sum_of_decoding_times / repetitions

print("Average Time Encoding for ",file_size_to_encode, "bytes: ", average_time_encoding)
print("Average Time Decoding for ",str(os.lstat(filename+".sbx").st_size), "bytes: ", average_time_decoding)

if os.path.exists(filename):
      os.remove(filename)
if os.path.exists(filename+".sbx"):
      os.remove(filename+".sbx")
if os.path.exists(filename+".sbx.raid"):
      os.remove(filename+".sbx.raid")
       


