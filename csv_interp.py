
"""
Simple linear interpolation on a 2 column csv file using numpy interpolation
Assumes a single header line in the csv, can be changed in 'genfromtxt' line below

Chris Meder
6/2/2020

"""

# Include standard modules
import os
import argparse
import pandas as pd
import numpy as np 
from numpy import genfromtxt

# Initiate the parser
parser = argparse.ArgumentParser()

# Add lshort arguments
parser.add_argument("-v", nargs='+', help="X values for interpolation, enter values in a space-delimited list [if -vf not specified]")
parser.add_argument("-vf", help="File containing X values for interpolation [if -v not specified]")
parser.add_argument("-i", required=True, help="Input filename in csv format, limited to 2 columns, assumes 1 header line [required]")
parser.add_argument("-o", help="Output filename [optional]")

# Read arguments from the command line
args = parser.parse_args()

# Get the input data file
if args.i:
	fin = args.i 
	print("File for interpolation: {}".format(fin))

#
# Get the desired x values for the interpolation
# 
# values list from command line
if args.v: 
	int_x = args.v
	print("Interpolate at X values: {}".format(int_x))

# values from file
elif args.vf:
	int_x_fin = args.vf
	# Read the csv into numpy arrays for interpolation
	data_int_x = genfromtxt(int_x_fin, delimiter=',', skip_header=0)
	int_x = data_int_x[:]
	print("Interpolate at X values: {}".format(int_x))

elif (not args.v) & (not args.vf): # Neither specified
	print("Values for interpolation not specified. Please specify -v or -vf.")
	exit()

# Read in the csv file using Pandas, just for an easy user preview
df = pd.read_csv(fin)
print("Head of input file is:\n {}".format(df.head()))

# Read the csv into numpy arrays for interpolation
data = genfromtxt(fin, delimiter=',', skip_header=1)

#
# Interpolate at specified values
#
# Assumes 1st column in data is X, 2nd column is Y
int_y = np.interp(int_x, data[:,0], data[:,1])

# Write results to the screen
print("Interpolated Y values:\n {}".format(int_y))

# Write the results to file, if requested
if args.o:
	fout = args.o 
	f = open(fout, 'wb')
	for i in range(len(int_x)):
		f.write("{},{}\n".format(int_x[i],int_y[i]).encode()) # .encode added for Python 3 compatibility
	f.close()

	print("Results written to file: {}".format(fout))
else:
	print("No output filename specified")	