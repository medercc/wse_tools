#!/usr/bin/env conda run -n gda python
"""
Created on Tue Jun  1 15:24:17 2021

Renames files based on user specified strings
@author: Chris.Meder
"""

import os
import sys
counter = 0

def usage():
    print("\nUsage: {} new_string old_string\n".format(sys.argv[0]))
    
path = os.getcwd()

# Get old and new strings from command line
if (len(sys.argv) < 2):
    print("No strings specified")
    usage()
    sys.exit()
elif (len(sys.argv) == 2):
    print("Please specify a new string for renaming")
    usage()
    sys.exit()
else:
    old_str = sys.argv[1]
    new_str = sys.argv[2]

for file in os.listdir(path):
    if file.find(old_str) > -1:
        counter = counter + 1
        src = os.path.join(path, file)
        dst = os.path.join(path, file.replace(old_str, new_str))
        #print("Src: {}".format(src))
        #print("Dst: {}".format(dst))
        os.rename(src, dst)

if counter == 0:
    print("No files with {} found".format(old_str))
    
