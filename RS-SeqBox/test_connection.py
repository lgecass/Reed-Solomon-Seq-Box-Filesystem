from reedsolo import RSCodec, ReedSolomonError
bytes_of_text= 2400
text= b'X' * bytes_of_text
print("LEN MESSAGE,",len(text))

redundancy=100

rsc=RSCodec(redundancy)

response = bytes(rsc.encode(text))
print("RESPONSE=", response)

print("LEN ENCODED", len(response))

decoded= bytes(rsc.decode(response)[0])

difference=len(response)-len(decoded)

print("Added redundancy Data",len(response)-len(decoded) )

