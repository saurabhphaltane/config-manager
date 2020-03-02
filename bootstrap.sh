#!/bin/bash 

sudo apt-get install python3.6 -y
sudo apt-get install python-yaml -y
sudo chmod 744 config-manager.py

# checking if python3 is installed
if [[ "$(python3 -V)" =~ "Python 3" ]];
then
	echo "Python 3 is installed"
else
	echo "Install Python 3"
fi
