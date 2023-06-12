f = open("1gb_file.txt", "w")
size = 1073741824 # bytes in 1 GiB
f.write("\1" * size)
f.close()