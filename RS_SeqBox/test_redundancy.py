import creedsolo.creedsolo as crs

bytes_of_text= 2334
redundancy=108
print(redundancy)

text= b'A' * bytes_of_text
print("LEN MESSAGE,",len(text))



rsc=crs.RSCodec(redundancy)

encoded_message = bytes(rsc.encode(bytearray(text)))

print("LEN ENCODED", len(encoded_message))
#print(encoded_message)
decoded_message = bytes(rsc.decode(bytearray(encoded_message))[0])

difference=len(encoded_message)-len(decoded_message)

print("difference",len(encoded_message)-len(decoded_message))
