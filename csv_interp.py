#!/usr/bin/env conda run -n gda python

"""
Python 3
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
import datetime
from numpy import genfromtxt
from scipy import interpolate

# Set date format for timeseries inut
DateFormat = '%Y-%M-%d %H:%M'

# Initiate the parser
parser = argparse.ArgumentParser()

# Add lshort arguments
parser.add_argument("-v", nargs='+', help="X values for interpolation, enter values in a space-delimited list [if -vf not specified]")
parser.add_argument("-vf", help="File containing X values for interpolation [if -v not specified]")
parser.add_argument("-ts", help="File containing timeseries with X values for interpolation [if -v or -vf not specified]")
parser.add_argument("-i", required=True, help="Input filename in csv format, limited to 2 columns, assumes 1 header line [required]")
parser.add_argument("-o", help="Output filename [optional]")
parser.add_argument("-outX", action='store_true', help="Output only Y values [optional]")
parser.add_argument("-e", action='store_true', help="Allow extrapolation")

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

# From timeseries file
elif args.ts:
	int_x_fin = args.ts # filename

	print(int_x_fin)
	# Check if the file exists
	try:
		with open(int_x_fin) as f:
			# Read the timeseries csv into pandas dataframe for interpolation
			data_int_df = pd.read_csv(f, names=['Datetime','int_x'], header=0)
			datetime=data_int_df['Datetime']
			int_x = data_int_df['int_x']
			print("Interpolate at X values: {}".format(int_x))

	except FileNotFoundError:
		print("File not found: {}".format(int_x_fin))
		exit()

elif (not args.v) & (not args.vf) & (not args.ts): # Neither specified
	print("Values for interpolation not specified. Please specify -v, -vf or -ts.")
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
		print("WARNING: X values for interpolation are outside input data range. Extrapolation occurred.")
else:
	# Use Numpy: holds values constant if int_x is outside range 
	int_y = np.interp(int_x, X, Y) 
	
	# Notify user if extrapolation occured, check for int_x outside of bounds
	if ((float(min(int_x)) < min(X)) or (float(max(int_x)) > max(X))):
		print("WARNING: X values for interpolation are outside input data range. Values were held constant at input data range limits.")

# Write results to the screen
print("Interpolated Y values:\n {}".format(str(int_y)))

# Write the results to file, if requested
if args.o:
	fout = args.o 

	# If this is a timeseries, write datetime index plus interpolated values
	if args.ts: 
		data_int_df['int_y'] = int_y
		data_int_df.set_index('Datetime', inplace=True)
		# If X values output requested, output int_x and int_y
		if args.outX:
			data_int_df.to_csv(fout, index_label='Datetime', columns=['int_x','int_y'], float_format='%.2f', date_format=DateFormat)
		# Otherwise just write out int_y
		else:
			data_int_df.to_csv(fout, index_label='Datetime', columns=['int_y'], float_format='%.2f', date_format=DateFormat)
	
	# Otherwise
	else:
		# If X values output requested, output int_x and int_y
		if args.outX:
			f = open(fout, 'wb')
			for i in range(len(int_x)):
				f.write("{},{}\n".format(int_x[i],int_y[i]).encode()) # .encode needed for Python 3 compatibility
			f.close()
		# Otherwise just write out int_y
		else: 
			f = open(fout, 'wb')
			for i in range(len(int_x)):
				f.write("{},{}\n".format(int_y[i]).encode()) # .encode needed for Python 3 compatibility
			f.close()

	print("Results written to file: {}".format(fout))
else:
	print("No output filename specified")	