
"""
1D linear interpolation on a 2 column csv file using scipy interpolation
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
from scipy import interpolate

# Initiate the parser
parser = argparse.ArgumentParser()

# Add lshort arguments
parser.add_argument("-v", nargs='+', help="X values for interpolation, enter values in a space-delimited list [if -vf not specified]")
parser.add_argument("-vf", help="File containing X values for interpolation [if -v not specified]")
parser.add_argument("-i", required=True, help="Input filename in csv format, limited to 2 columns, assumes 1 header line [required]")
parser.add_argument("-o", help="Output filename [optional]")
parser.add_argument("-e", action='store_true', help="Extrapolation allowed")

# Read arguments from the command line
args = parser.parse_args()

# Get the input data file
if args.i:
	fin = args.i # filename

	# Check if the file exists
	try:
		with open(fin) as f:
			print("Input data file: {}".format(fin))
			# Read the input csv into numpy arrays for interpolation
			# Assumes 1st column in data is X, 2nd column is Y
			data = genfromtxt(fin, delimiter=',', skip_header=1)
			X = data[:,0]
			Y = data[:,1]
			
			# Read in the csv file using Pandas, just for an easy user preview
			df = pd.read_csv(fin)
			print("Head of input file is:\n {}".format(df.head()))

	except FileNotFoundError:
		print("File not found: {}".format(fin))
		exit()

#
# Get X values for the interpolation
# 

# List from command line
if args.v: 
	int_x = args.v # filename
	print("Interpolate at X values:\n {}".format(int_x))

# From file
elif args.vf:
	int_x_fin = args.vf # filename

	# Check if the file exists
	try:
		with open(int_x_fin) as f:
		# Read the csv into numpy arrays for interpolation
			data_int_x = genfromtxt(int_x_fin, delimiter=',', skip_header=0)
			int_x = data_int_x[:]
			print("Interpolate at X values: {}".format(int_x))

	except FileNotFoundError:
		print("File not found: {}".format(int_x_fin))
		exit()

elif (not args.v) & (not args.vf): # Neither specified
	print("Values for interpolation not specified. Please specify -v or -vf.")
	exit()

#
# Interpolate at specified values
#
if args.e:
	# Use Scipy: allows extrapolation
	f = interpolate.interp1d(X, Y, fill_value='extrapolate')
	int_y = f(int_x)

	# Notify user if extrapolation occured, check for int_x outside of bounds
	if ((float(min(int_x)) < min(X)) or (float(max(int_x)) > max(X))):
		print("WARNING: X values for interpolation outside input data range. Extrapolation occurred.")
else:
	# Use Numpy: holds values constant if int_x is outside range 
	int_y = np.interp(int_x, X, Y) 
	
	# Notify user if extrapolation occured, check for int_x outside of bounds
	if ((float(min(int_x)) < min(X)) or (float(max(int_x)) > max(X))):
		print("WARNING: X values for interpolation outside input data range. Values held constant.")

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