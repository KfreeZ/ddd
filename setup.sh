#!/bin/sh

sudo apt-get install python-dev

sudo tar -xzf crc16-0.1.1.tar.gz
cd ~/ddd/crc16-0.1.1
sudo python setup.py build
sudo python setup.py install

pip install bitstring

pip install requests

sudo apt-get install samba samba-common-bin

sudo sambapasswd -a ddd

sudo cp ~/ddd/smb.conf /etc/samba/smb.conf
