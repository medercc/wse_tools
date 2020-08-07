#!/usr/bin/env conda run -n gda python

"""
Scales longterm Seatac precipitation record and extends it with a local gage record.

- User specifies Seatac (or any other) longterm record, local gage record, multiplier for Seatac, and a replacement record for specific dates if desired
- Converts local time in the local gage to a consistent, non-daylight savings standard time (ie. PDT will become PST)
- Scales Seatac by a user-specified factor
- Truncates Seatac record at the first timestamp of the local gage
- Concatenates the scaled, truncated Seatac record with the local gage
- Replaces specific values called out in a replacement record file
- No filling or interpolation of missing data occurs
- Returns: complete concatenated record, list of datetimes for which gap to next timestep is > 15 mins, and a plot of all the records

Chris Meder
June 2020

"""

# Standard package imports
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
# Seaborn settings
sns.set(style="darkgrid")
#sns.set_palette(sns.set_palette('colorblind'))
sns.set_palette(sns.set_palette('pastel'))

#
# USER INPUT
#

# Seatac gage
sea_fn = 'Seatac_15min_Precip_1948-2010.csv'
sea_HeaderLines = 0 # 0-based
sea_ColNames = ['Datetime','Precip Raw (in)'] # assumes 2 columns of data, named as labeled here. Input names don't matter.  
sea_Delimiter = ','
sea_Scalar = 1.26 # scalar to apply to SeaTac precip
# Local gage
local_fn = 'BlackDiamond_precip.csv' # csv file containing local gage precip record
local_HeaderLines = 0 # 0-based
#local_ColNames = ['Gage','Collect Time (UTC)','Collect Time (Local)','Precip (in)','Notes'] # assumes these column names based on standard KC gage headers 
local_ColNames = ['Collect Date (UTC)','Precipitation (inches)'] # Read only these assumed column names based on standard KC gage headers 
dtypes = {'Collect Date (UTC)': 'str', 'Precipitation (inches)': 'float'} # tell Pandas the data type for each column
parse_dates = ['Collect Date (UTC)']
local_Delimiter = ','
# Replacement record
replace = False # True / False: True if you want to implement precip value replacement changes at specified datetimes in the record, otherwise set to False 
repl_fn = 'Enumclaw_repl_record.csv'
repl_HeaderLines = 0 # 0-based
repl_ColNames = ['Datetime','Precip (in)'] # assumes these column names based on standard KC gage headers 
repl_Delimiter = ','
# Scaled, extended record output filename
out_fn = 'Seatac_15min_Precip_Scale_Extended_with_BlackDiamond.csv'
# Plot filename
plot_fn = out_fn[:-4]+'_plot.png'

# END USER INPUT

# 
# Seatac record
#

# Read Seatac gage precip
print("Reading Seatac record: {}".format(sea_fn))
sea_df = pd.read_csv(sea_fn, delimiter=sea_Delimiter, header=sea_HeaderLines, names=sea_ColNames, index_col=False)

# Convert datetimes to datetime64 
sea_df['Datetime'] = pd.to_datetime(sea_df['Datetime'])

# Set Datetime to index
sea_df.set_index(sea_df['Datetime'], inplace=True)

# Drop Datetime column
sea_df.drop(columns=['Datetime'], inplace=True)

# Apply scalar to precip raw (the resulting scaled precip is stored as 'Precip (in)' to enable concatenation below)
print("Scaling Seatac precip by {}".format(sea_Scalar))
sea_df['Precip (in)'] = sea_df['Precip Raw (in)'] * sea_Scalar

#
# Local record
#

# Read local gage precip
print("Reading local record: {}".format(local_fn))
local_df = pd.read_csv(local_fn, dtype=dtypes, parse_dates=parse_dates, delimiter=local_Delimiter, header=local_HeaderLines, usecols=local_ColNames, index_col=False)

# Convert datetimes to datetime64 
local_df['Collect Date (UTC)'] = pd.to_datetime(local_df['Collect Date (UTC)'])

# Shift Collect Time (UTC) by 8 hrs to get PST (no daylight savings time)
local_df['Datetime (PST)'] = local_df['Collect Date (UTC)'] - timedelta(hours=8)

# Set Datetime to index
local_df.set_index(local_df['Datetime (PST)'], inplace=True)

# Find time delta between each timestep
local_df['Delta'] = local_df['Datetime (PST)'] - local_df['Datetime (PST)'].shift()

# Create new df of timesteps where the time delta next data point in the record is greater than 15 mins (report this below)
local_missing_df = local_df[local_df['Delta'] > timedelta(hours=0.25)]

# Drop unnecessary columns from local gage df
local_df.drop(columns=['Collect Date (UTC)','Datetime (PST)','Delta'], inplace=True)

#
# Stitch the two gage records together at the overlap point
#

# First, truncate the Seatac record which ends at the timestep where the local gage record begins
print("Concatenating records")
print("Truncating Seatac record at {}".format(local_df.index[0]))
sea_trunc_df = sea_df[sea_df.index < local_df.index[0]]

# Concatenate the Seatac and local gage records
extend_df = pd.concat([sea_trunc_df, local_df])

# Drop unnecessary columns
extend_df.drop(columns=['Precip Raw (in)'], inplace=True)

#
# Replacement record (select dates to fill with particular value) 
#

# if the user requested this...
if replace:
	# Read the replacement record of select dates
	print("Reading replacement record: {}".format(repl_fn))
	repl_df = pd.read_csv(repl_fn, delimiter=repl_Delimiter, header=repl_HeaderLines, names=repl_ColNames, index_col=False)

	# Convert datetimes to datetime64 
	repl_df['Datetime'] = pd.to_datetime(repl_df['Datetime'])

	# Set Datetime to index, then drop the old Datetime column
	repl_df.set_index(repl_df['Datetime'], inplace=True)
	repl_df.drop(columns=['Datetime'], inplace=True)

	# Perform the replacement of precip values at specified dates
	print("Replacing specified values")
	extend_df.update(repl_df)

#
# Write output
#

# Write out scaled, extended gage record to csv
try:
	print("Writing extended record to file: {}".format(out_fn))
	extend_df.to_csv(out_fn, index_label=['Datetime'], float_format='%.3f')
except IOError:
	print("Could not write output file")

# Write out timestamps where the gap to the next timestamp is > 15 mins
try:
	tsgaps_fn = out_fn[:-4]+'_Gaps_GT_15min.txt'
	print("Writing timestamps with gap to next timestamp > 15 mins to file: {}".format(tsgaps_fn))
	local_missing_df.to_csv(tsgaps_fn, index_label=['Datetime'], columns=['Delta'])
except IOError:
	print("Could not write output file")

# Make a quick plot
f, ax = plt.subplots(figsize=(20,12))

ax.plot(extend_df.index, extend_df['Precip (in)'], label='Final Scaled, Extended', zorder=1)
ax.plot(local_df.index, local_df['Precipitation (inches)'], label='Local Gage Raw', linestyle=':', zorder=2)
ax.plot(sea_df.index, sea_df['Precip Raw (in)'], label='Seatac Gage Raw', linestyle=':', zorder=3)  
if replace:
    ax.scatter(repl_df.index, repl_df['Precip (in)'], label='Replacement Record', color='red', zorder=10)
ax.legend()
ax.set_ylabel('Precipitation (inches)')
ax.set_title('Scaled, Extended Precipitation Based on Seatac Longterm Record')
try:
	plt.savefig(plot_fn, bbox_inches='tight')
	print("Plot file saved as: {}".format(plot_fn))
except IOError:
	print("Could not write plot")