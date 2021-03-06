#!/usr/bin/env conda run -n gda python

"""
Python 3
1D linear interpolation on a 2 column csv file using scipy interpolation
Assumes a single header line in the csv, can be changed in 'genfromtxt' line below

Inputs:
- X values AT which to interpolate. These data may be specified in one of three ways:
	1. A space-delimited list of the values entered on the command line (-X argument)
	2. A text file containing the values (-Xf argument)
	3. A csv file timeseries containing the values, assumes first column is datetime and second column contains the X values (-Xts argument)
- X,Y data FROM which to interpolate. Specified in csv file format (-i argument)

Outputs:
- Y values interpolated at the requested X values, in csv file format
- If the X values were specified in a timeseries, the timeseries is written to the output with the Y values
- If the X values in the timeseries are desired in the output file, use the -outX argument 

Extrapolation is not allowed by default, but can be requested by specifying the -e option

Chris Meder
9/2/2020

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
parser.add_argument("-X", nargs='+', help="X values for interpolation, enter values in a space-delimited list [if -Xf or -Xts not specified]")
parser.add_argument("-Xf", help="File containing X values for interpolation [if -X and -Xts not specified]")
parser.add_argument("-Xts", help="File containing timeseries with X values for interpolation, assumes first column is datetime and second column contains the X values [if -X or -Xf not specified]")
parser.add_argument("-i", required=True, help="Input filename in csv format, limited to 2 columns, assumes 1 header line [required]")
parser.add_argument("-o", help="Output filename [optional]")
parser.add_argument("-outX", action='store_true', help="Output the requested X values [optional]")
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
if args.X: 
	int_x = args.X # filename
	print("Interpolate at X values:\n {}".format(int_x))

# From file
elif args.Xf:
	int_x_fin = args.Xf # filename

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
elif args.Xts:
	int_x_fin = args.Xts # filename

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

elif (not args.X) & (not args.Xf) & (not args.Xts): # Neither specified
	print("Values for interpolation not specified. Please specify -X, -Xf or -Xts.")
	exit()

#
# Interpolate at specified values
#

# If extrapolation was specified
if args.e:
	# Use Scipy: allows extrapolation, but does not handle ignoring values of -901
	f = interpolate.interp1d(X, Y, fill_value='extrapolate')
	int_y = f(int_x)

	# Notify user if extrapolation occured, check for int_x outside of bounds
	if ((float(min(int_x)) < min(X)) or (float(max(int_x)) > max(X))):
		print("WARNING: X values for interpolation are outside input data range. Extrapolation occurred.")

# No extrapolation
else:
	# Use Numpy: holds values constant if int_x is outside range 
	UNDEF = -901.0 # this value will not be interpolated, it will output int_y = -901
	int_y = np.interp(int_x, X, Y, left=UNDEF) 

	# Notify user if extrapolation occured, check for int_x outside of bounds
	if ((float(min(int_x)) < min(X)) or (float(max(int_x)) > max(X))):
		print("WARNING: X values for interpolation are outside input data range. Values were held constant at input data range limits.")

# Write results to the screen
print("Interpolated Y values:\n {}".format(int_y))

# Write the results to file, if requested
if args.o:
	fout = args.o 

	# If this is a timeseries, write datetime index plus interpolated values
	if args.Xts: 
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