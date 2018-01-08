#!/bin/bash



FILE="gather.dat"

ssh mocohen@comet.sdsc.xsede.org -t "xdusage -a -p TG-MCA94P017" > $FILE

python run_weekly.py 

