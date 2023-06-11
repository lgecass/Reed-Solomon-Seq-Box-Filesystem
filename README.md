# Reed-Solomon-Seq-Box-Filesystem
A data preservation and recovery focused filesystem enhanced with Reed-Solomon Data error correction and Seq-Box data block recognition <br/>
Files after being placed into the mounted Folder are copied and encoded. <br/>
Everytime you read it should compare the Hashes between these 2 files and repair the file if needed. <br/>
The .sbx File represents the original file and is the only file you need to replace your original data. <br/>
The .sbx file does not depend on the original file. <br/>

## Installation
### Requirements
python >= 3.6
libfuse 3 | https://github.com/libfuse/libfuse<br/>
reedsolo | `pip install reedsolo`<br/>
pyfuse3 | `pip install pyfuse3`<br/>
### Full Installation Steps
`git clone https://github.com/lgecass/Reed-Solomon-Seq-Box-Filesystem.git`<br/>
`cd Reed-Solomon-Seq-Box-Filesystem`<br/>
`pip install -r requirements.txt`<br/>
`git clone https://github.com/libfuse/libfuse.git`<br/>
`cd libfuse`<br/>
`mkdir build; cd build`<br/>
`meson setup ..`<br/>
`ninja`<br/>
`sudo ninja install`<br/>

## Usage
### Mount filesystem
`python ./RS_SeqBox/Sbx_Rsc_filesystem.py working_directory shield_directory`
<br/>
working_directory keeps files while filesystem is mounted. 
<br/>
shield_directory keeps files permanently even after the filesystem is unmounted.
### Unmount Filesystem
`umount -l destinationmount`

## Recover Files from corrupted data drive
### Make an Image file out of the Partition where files cannot be recognized
`sudo dd if=/dev/<data_drive_partition> of=image.ima bs=1M status=progress`
### Scan the Image for Files
`python ./RS_SeqBox/sbxscan.py image.ima` <- This creates a .db3 file
### Preview all the files that had been recognized by scanning
`python ./RS_SeqBox/sbxreco.py sbxscan.db3 -i`
### Recover All Files
`python ./RS_SeqBox/sbxreco.py sbxscan.db3 --all`
### Decode Files into their normal Fileformat
`python ./RS_SeqBox/sbxdec.py <file to decode>`
## Code Attribution and Modifications
Some of the code in this repository is based on the work of Marco Pontello (© 2017). The original code can be found here (https://github.com/MarcoPon/SeqBox). <br/> 
### I have made the following modifications: <br/>
`...`
