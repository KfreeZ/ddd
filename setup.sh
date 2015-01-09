#!/bin/sh

sudo apt-get install python-dev

sudo tar -xzf crc16-0.1.1.tar.gz
cd /home/pi/ddd/crc16-0.1.1
sudo python setup.py build
sudo python setup.py install

sudo apt-get install python-pip

pip install bitstring

pip install requests

sudo apt-get install samba samba-common-bin

sudo smbpasswd -a ddd

sudo cp /home/pi/ddd/smb.conf /etc/samba/smb.conf
