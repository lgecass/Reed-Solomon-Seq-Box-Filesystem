# Reed-Solomon-Seq-Box-Filesystem
A data preservation and recovery focused filesystem enhanced with Reed-Solomon Data error correction and Seq-Box data block recognition <br/>
Files after being placed into the mounted Folder are copied and encoded. <br/>
Everytime you read it should compare the Hashes between these 2 files and repair the file if needed. <br/>
The .sbx File represents the original file and is the only file you need to replace your original data. <br/>

## Installation
### Requirements
libfuse 3 | https://github.com/libfuse/libfuse<br/>
reedsolo | `pip install reedsolo`<br/>
pyfuse3 | `pip install pyfuse3`<br/>

## Usage
### Mount filesystem
`python ./RS-SeqBox/Sbx_Rsc_filesystem.py sourcemount destinationmount`
### Unmount Filesystem
`umount -l destinationmount`

## Recover Files from corrupted data drive
### Make an Image file out of the Partition where files cannot be recognized
`sudo dd if=/dev/<data_drive_partition> of=image.ima bs=1M status=progress`
### Scan the Image for Files
`python ./RS-SeqBox/sbxscan.py image.ima` <- This creates a .db3 file
### Preview all the files that had been recognized by scanning
`python ./RS-SeqBox/sbxreco.py sbxscan.db3 -i`
### Recover All Files
`python ./RS-SeqBox/sbxreco.py sbxscan.db3 --all`
### Decode Files into their normal Fileformat
`python ./RS-SeqBox/sbxdec.py <file to decode>`
