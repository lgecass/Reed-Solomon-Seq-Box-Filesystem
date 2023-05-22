import sbxenc
import sbxdec
from reedsolo import RSCodec, ReedSolomonError
text=b"H"
print("LEN MESSAGE,",len(text))
redundancy=32
rsc=RSCodec(redundancy)
response = bytes(rsc.encode(text))
print("LEN ENCODEDE", len(response))
decoded= bytes(rsc.decode(response)[0])
print(response)
difference=len(response)-len(decoded)
print("difference",len(response)-len(decoded) )
print("Redundancy times:",difference/redundancy )
#sbxenc.encode(filename="./test.txt", overwrite=True)
#sbxdec.decode(sbxfilename="./shield_mirror/Folien_Vorlesung7.pdf.sbx",overwrite=True)