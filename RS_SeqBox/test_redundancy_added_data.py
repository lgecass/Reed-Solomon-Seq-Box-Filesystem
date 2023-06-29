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

import creedsolo.creedsolo as crs

bytes_of_text= 1000
redundancy=200
print("Redundancy Symbols used:",redundancy)

text= b'A' * bytes_of_text
print("LEN MESSAGE,",len(text))

rsc=crs.RSCodec(redundancy)

encoded_message = bytes(rsc.encode(bytearray(text)))

print("LEN ENCODED", len(encoded_message))

decoded_message = bytes(rsc.decode(bytearray(encoded_message))[0])

difference=len(encoded_message)-len(decoded_message)

print("difference",len(encoded_message)-len(decoded_message))
