import sbxenc as encoder
import sbxdec as decoder


encoder.encode("RS_SeqBox/test.txt",overwrite=True)

decoder.decode("RS_SeqBox/test.txt.sbx",overwrite=True)