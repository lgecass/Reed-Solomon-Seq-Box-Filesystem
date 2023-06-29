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

import os
import random
import threading

def create_fragmented_files(directory, num_files, max_file_size,num_thread):
   

    for i in range(num_files):
        file_name = "fileImportant"+str(num_thread)+str(i)+".txt"
        file_path = os.path.join(directory, file_name)

        # Generate a random file size
        file_size = random.randint(1, max_file_size)
        
        # Create a file with unique data
        with open(file_path, "wb") as file:
            file.write(os.urandom(file_size))
        file.close()

# Specify the directory where the files will be created
directory = "/path/to/directory/where/files/should/be/created"
if not os.path.exists(directory):
        os.makedirs(directory)
# Specify the number of files to create
num_files = 10

# Specify the maximum file size in bytes
max_file_size = 5000000

# Call the function to create the fragmented files
x = threading.Thread(target=create_fragmented_files, args=(directory,num_files,max_file_size,1))
y = threading.Thread(target=create_fragmented_files, args=(directory,num_files,max_file_size,2))
z = threading.Thread(target=create_fragmented_files, args=(directory,num_files,max_file_size,3))
x.start()
y.start()
z.start()
x.join()
y.join()
z.join()