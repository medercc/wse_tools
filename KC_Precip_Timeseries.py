#!/usr/bin/env conda run -n gda python

"""
Process raw King County precipitation gage data to produce a two column, comma-separated timeseries with daylight savings time shifts removed

Input: Raw King County gage data in csv format
- Reads columns: 'Collect Date (UTC)', 'Precipitation (inches)'
- Removes daylight savings time, setting local time equal to UTC - 8 hours
Returns: Two column precipitation timeseries in csv format, check plot, list dates with record gaps greater than 15 minutes  

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
sns.set_palette(sns.set_palette('pastel')) # 'colorblind'

#
# USER INPUT
#

# Local gage
local_fn = 'MiddleGreen_precip.csv' # csv file containing local gage precip record
HeaderLines = 0 # 0-based
ColNames = ['Collect Date (UTC)','Precipitation (inches)'] # Read only these assumed column names based on standard KC gage headers 
dtypes = {'Collect Date (UTC)': 'str', 'Precipitation (inches)': 'float'} # tell Pandas the data type for each column
parse_dates = ['Collect Date (UTC)']
Delimiter = ','
# Replacement record
replace = False # True / False: True if you want to implement precip value replacement changes at specified datetimes in the record, otherwise set to False 
repl_fn = 'repl_record.csv'
repl_HeaderLines = 0 # 0-based
repl_ColNames = ['Datetime','Precip (in)'] # assumes these column names based on standard KC gage headers 
repl_Delimiter = ','
# Output filename
out_fn = 'MiddleGreen_precip_ts.csv'
# Plot filename
plot_fn = out_fn[:-4]+'_plot.png'

# END USER INPUT

#
# Local record
#

# Read local gage precip
print("Reading local record: {}".format(local_fn))
local_df = pd.read_csv(local_fn, dtype=dtypes, parse_dates=parse_dates, delimiter=Delimiter, header=HeaderLines, usecols=ColNames, index_col=False)

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
	local_df.update(repl_df)

#
# Write output
#

# Write out gage record to csv
try:
	print("Writing local record to file: {}".format(out_fn))
	local_df.to_csv(out_fn, index_label=['Datetime'], float_format='%.3f')
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

ax.plot(local_df.index, local_df['Precipitation (inches)'], label='Local Gage Raw')
if replace:
    ax.scatter(repl_df.index, repl_df['Precip (in)'], label='Replacement Record', color='red')
ax.legend()
ax.set_ylabel('Precip (in)')
ax.set_title('Precipitation')
try:

	plt.savefig(plot_fn, bbox_inches='tight')
	print("Plot file saved as: {}".format(plot_fn))
except IOError:
	print("Could not write plot")