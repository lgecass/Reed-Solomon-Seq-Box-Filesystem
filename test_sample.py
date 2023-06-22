import RS_SeqBox.sbxenc as Encoder
import RS_SeqBox.sbxdec as Decoder
import os
import pytest
from reedsolo import ReedSolomonError 

#Helper method to create files
def create_file(filename,content):
    with open(filename, 'w') as file:
        file.write(content)

#VERSION 1 encode tests for calling internal encode() method
def test_encode_ver1_existence_of_file():
    create_file("test_file.txt", 'Hello'*200)
    Encoder.encode("test_file.txt")
    assert os.path.exists("test_file.txt.sbx")

def test_encode_ver1_file_is_right_size():
    create_file("test_file.txt", 'Hello'*200)
    Encoder.encode("test_file.txt")
    assert os.lstat("test_file.txt.sbx").st_size == 2560

def test_encode_ver1_file_correctly_decoded():
    create_file("test_file.txt", 'Hello'*200)
    Encoder.encode("test_file.txt")
    try:
        Decoder.decode("test_file.txt.sbx", overwrite=True)
    except ReedSolomonError as rserr:
        print("Decoding not correct")
        assert False
    assert True

#VERSION 2 encode tests for calling internal encode() method
def test_encode_ver2_existence_of_file():
    create_file("test_file.txt", 'Hello'*200)
    Encoder.encode("test_file.txt", sbx_ver=2)
    assert os.path.exists("test_file.txt.sbx")

def test_encode_ver2_file_is_right_size():
    create_file("test_file.txt", 'Hello'*200)
    Encoder.encode("test_file.txt",sbx_ver=2)
    assert os.lstat("test_file.txt.sbx").st_size == 8192

def test_encode_ver2_file_correctly_decoded():
    create_file("test_file.txt", 'Hello'*200)
    Encoder.encode("test_file.txt",sbx_ver=2)
    try:
        Decoder.decode("test_file.txt.sbx", overwrite=True,sbx_ver=2)
    except ReedSolomonError as rserr:
        print("Decoding not correct")
        assert False
    assert True


#VERSION 1 encode tests for calling internal main Method
def test_main_ver1_existence_of_file():
    create_file("test_file.txt", 'Hello'*200)
    os.system("python ./RS_SeqBox/sbxenc.py test_file.txt")
    assert os.path.exists("test_file.txt.sbx")

def test_main_ver1_file_is_right_size():
    create_file("test_file.txt", 'Hello'*200)
    os.system("python ./RS_SeqBox/sbxenc.py test_file.txt")
    assert os.lstat("test_file.txt.sbx").st_size == 2560

def test_main_ver1_file_correctly_decoded():
    create_file("test_file.txt", 'Hello'*200)
    os.system("python ./RS_SeqBox/sbxenc.py test_file.txt")
    try:
        os.system("python ./RS_SeqBox/sbxdec.py test_file.txt overwrite=True")
    except ReedSolomonError as rserr:
        print("Decoding not correct")
        assert False
    assert True

#VERSION 2 encode tests for calling internal main method
def test_main_ver2_existence_of_file():
    create_file("test_file.txt", 'Hello'*200)
    os.system("python ./RS_SeqBox/sbxenc.py test_file.txt --sbxver 2 ")
    assert os.path.exists("test_file.txt.sbx")

def test_main_ver2_file_is_right_size():
    create_file("test_file.txt", 'Hello'*200)
    os.system("python ./RS_SeqBox/sbxenc.py test_file.txt --sbxver 2")
    assert os.lstat("test_file.txt.sbx").st_size == 8192

def test_main_ver2_file_correctly_decoded():
    create_file("test_file.txt", 'Hello'*200)
    os.system("python ./RS_SeqBox/sbxenc.py test_file.txt --sbxver 2")
    try:
        os.system("python ./RS_SeqBox/sbxdec.py test_file.txt --sbxver 2")
    except ReedSolomonError as rserr:
        print("Decoding not correct")
        assert False
    assert True

#Version 1 test correct decoded and encoded names
def test_encoded_correct_name_in_encode_method():
    create_file("test_file.txt", 'Hello'*200)
    Encoder.encode("test_file.txt", "test_file_my_wish.txt.sbx")
    assert os.path.exists("test_file_my_wish.txt.sbx")

def test_decoded_correct_name_in_encode_method():
    create_file("test_file.txt", 'Hello'*200)
    Encoder.encode("test_file.txt")
    Decoder.decode("test_file.txt.sbx", "test_file_other.txt")
    assert os.path.exists("test_file_other.txt")

def test_encoded_correct_name_in_main_method():
    create_file("test_file.txt", 'Hello'*200)
    os.system("python ./RS_SeqBox/sbxenc.py test_file.txt test_file_my_wish.txt.sbx")
    assert os.path.exists("test_file_my_wish.txt.sbx")

def test_decoded_correct_name_in_main_method():
    create_file("test_file.txt", 'Hello'*200)
    os.system("python ./RS_SeqBox/sbxenc.py test_file.txt")
    os.system("python ./RS_SeqBox/sbxdec.py test_file.txt.sbx test_file_other.txt")
    assert os.path.exists("test_file_other.txt")


@pytest.fixture(autouse=True)
def cleanup():
    yield
    if os.path.exists("test_file.txt"):
        os.remove("test_file.txt")
    if os.path.exists("test_file.txt.sbx"):
        os.remove("test_file.txt.sbx")
    if os.path.exists("test_file_other.txt"):
        os.remove("test_file_other.txt")    
    if os.path.exists("test_file_my_wish.txt.sbx"):
        os.remove("test_file_my_wish.txt.sbx")
        