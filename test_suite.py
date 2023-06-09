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
import RS_SeqBox.sbxenc as Encoder
import RS_SeqBox.sbxdec as Decoder
import RS_SeqBox.sbxcheck as sbxChecker
import os
import pytest
from reedsolo import ReedSolomonError 
import subprocess
import time
import shutil
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

def test_if_raid_gets_created():
    create_file("test_file.txt", 'Hello'*200)
    os.system("python ./RS_SeqBox/sbxenc.py test_file.txt -raid")
    assert os.path.exists("test_file.txt.sbx.raid")

def test_if_raid_works():
    create_file("test_file.txt", 'Hello'*200)
    os.system("python ./RS_SeqBox/sbxenc.py test_file.txt -raid")
    data = b'A'*512
    with open("test_file.txt.sbx", "r+b") as file:
        file.seek(0)  
        file.write(data[:512])  
    os.remove("test_file.txt")
    os.system("python ./RS_SeqBox/sbxdec.py test_file.txt.sbx -o -raid")
    assert os.path.exists("test_file.txt")

def test_if_sbxcheck_recovers_data():
    os.mkdir("testfolder")
    create_file("./testfolder/test_file.txt", 'Hello'*200)
    Encoder.encode(filename="./testfolder/test_file.txt", sbxfilename="./testfolder/test_file.txt.sbx", raid=True)
    data = b'A'*100
    with open("./testfolder/test_file.txt", "r+b") as file:
        file.seek(0)  
        file.write(data[:100]) 
    sbxChecker.check("./testfolder", auto=True, raid=True)
    with open('./testfolder/test_file.txt', 'rb') as file:
        first_byte = file.read(1)
        assert first_byte == b'H'

def test_if_sbxcheck_recovers_data_with_password():
    os.mkdir("testfolder")
    create_file("./testfolder/test_file.txt", 'Hello'*200)
    Encoder.encode(filename="./testfolder/test_file.txt", sbxfilename="./testfolder/test_file.txt.sbx", raid=True, password="1234")
    data = b'A'*100
    with open("./testfolder/test_file.txt", "r+b") as file:
        file.seek(0)  
        file.write(data[:100]) 
    sbxChecker.check("./testfolder", auto=True, raid=True, password="1234")
    with open('./testfolder/test_file.txt', 'rb') as file:
        first_byte = file.read(1)
        assert first_byte == b'H'

def test_if_password_encoding_works():
    create_file("test_file_encoding.txt", 'A'*500)
    Encoder.encode(filename="test_file_encoding.txt",sbxfilename="test_file_encoding.txt.sbx", password="1234")
    with open("test_file_encoding.txt.sbx", "r+b") as file:
        file.seek(528)  
        assert file.read(1) == b'p'

def test_if_password_decoding_works():
    create_file("test_file_encoding.txt", 'A'*500)
    Encoder.encode(filename="test_file_encoding.txt",sbxfilename="test_file_encoding.txt.sbx", password="1234")
    Decoder.decode(sbxfilename="test_file_encoding.txt.sbx",filename="test_file_encoding.txt", password="1234",overwrite=True)
    with open("test_file_encoding.txt", "r+b") as file:
        file.seek(0)  
        assert file.read(1) == b'A'            

@pytest.fixture(autouse=True)
def cleanup():
    yield
    
    if os.path.exists("test_file.txt"):
        os.remove("test_file.txt")

    if os.path.exists("test_file.txt.sbx"):
        os.remove("test_file.txt.sbx")

    if os.path.exists("test_file.txt.sbx.raid"):
        os.remove("test_file.txt.sbx.raid")

    if os.path.exists("test_file_other.txt"):
        os.remove("test_file_other.txt")    

    if os.path.exists("test_file_my_wish.txt.sbx"):
        os.remove("test_file_my_wish.txt.sbx")
    
    if os.path.exists("./testfolder/test_file.txt"):
        os.remove("./testfolder/test_file.txt")
    
    if os.path.exists("./testfolder/test_file.txt.sbx"):
        os.remove("./testfolder/test_file.txt.sbx")
    
    if os.path.exists("./testfolder/test_file.txt.sbx.raid"):
        os.remove("./testfolder/test_file.txt.sbx.raid")
    
    if os.path.exists("testfolder"):
        os.removedirs("testfolder")

    if os.path.exists("test_file_encoding.txt"):
        os.remove("test_file_encoding.txt")

    if os.path.exists("test_file_encoding.txt.sbx"):
        os.remove("test_file_encoding.txt.sbx")