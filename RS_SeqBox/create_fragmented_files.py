import os
import random
import threading

def create_fragmented_files(directory, num_files, max_file_size,num_thread):
    if not os.path.exists(directory):
        os.makedirs(directory)

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
directory = "/home/luge/Desktop/working_directory"

# Specify the number of files to create
num_files = 40

# Specify the maximum file size in bytes
max_file_size = 2245000

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