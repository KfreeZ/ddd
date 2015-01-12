#!/bin/sh

sudo apt-get install python-dev

sudo tar -xzf crc16-0.1.1.tar.gz
cd /home/pi/ddd/crc16-0.1.1
sudo python setup.py build
sudo python setup.py install

sudo apt-get install python-pip

sudo pip install bitstring

sudo pip install requests

sudo apt-get install samba samba-common-bin

sudo smbpasswd -a pi

sudo cp /home/pi/ddd/smb.conf /etc/samba/

sudo cp /home/pi/ddd/rc.local /etc/

sudo cp /home/pi/ddd/cmdline.txt /boot/

sudo cp /home/pi/ddd/inittab /etc/
