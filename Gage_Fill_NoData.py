#!/usr/bin/env conda run -n gda python

"""
Fills missing data in the input gage record.

- User defines several parameters including desired timestep and maximum timestep gap over which to interpolate
- Converts local time to a consistent, non-daylight savings standard time (ie. PDT will become PST)
- Rounds all input timeseries values to the nearest 15 minutes
- Creates a continuous timeseries based on time range of the input data
- Interpolates missing data in the gage record for which the timestep range is less than MaxGap
- Returns: filled timeseries file, summary of missing and interpolated timestamps, and a check plot  

Based on Tim Tschetter script

Chris Meder
June 2020

"""

# Standard package imports
import re
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import pandas_bokeh
import seaborn as sns
# Seaborn settings
sns.set(style="darkgrid")
#sns.set_palette(sns.set_palette('colorblind'))
sns.set_palette(sns.set_palette('pastel'))

#
# USER INPUTS
#
FileName = 'ParadiseCreek_USGS_13346800_15min_2018-2020.txt'
Agency = "USGS" # KC (King County) or USGS 
Timestep = 15 # in minutes
MaxGap = 180 # in minutes
DateFormat = '%Y-%m-%d %H:%M' # Format for export only, any datetime format is read in by Pandas, and converted once in memory

# Set file read parameters
if Agency == "KC": # King County
	HeaderLines = 0 # number of header lines, 0-based (0 is 1 header line), varies with gage and agency
	ColumnNames = ['Site_Code','Collect Date (UTC)','Collect Date (local)','Stage','Discharge'] # should be fixed
	Delimiter = ','

elif Agency == "USGS":
	HeaderLines = 32 # number of header lines, 0-based (0 is 1 header line), varies with gage and agency
	ColumnNames = ['Agency','Gage_ID','Datetime','Timezone','Discharge','Notes'] # Notes 'Discharge' may be 'Stage', as long as it's in the same column location in the input
	dtypes = {'Agency': 'str', 'Gage_ID': 'str', 'Discharge': 'float', 'Notes': 'str'} # tell Pandas the data type for each column
	TimeZone = 'PDT' # enter the daylight savings shorthand for timezone in the USGS gage data
	Delimiter = '\s{2,}'  # tab-delimited: '\t', multiple space-delimited: '\s{2,}'
#
# END USER INPUTS
#

# Load the gage data into a Pandas dataframe
# 'engine='python' argument is required to properly implement the delimiter if it is a multiple whitespace character (\s{2,})
print("Reading input file: {}".format(FileName))
df = pd.read_csv(FileName, dtype=dtypes, delimiter=Delimiter, header=HeaderLines, names=ColumnNames, index_col=False, engine='python')

# Manage timestamps
if Agency == "KC": # King County
	# Convert to datetime64 format 
	df['Collect Date (UTC)'] = pd.to_datetime(df['Collect Date (UTC)'])

	# Round Datetime to the nearest 15 mins
	df['Collect Date (UTC)'] = df['Collect Date (UTC)'].dt.round('15min') 

	# Create new Datetime column for analysis equal to UTC shifted by 8 hrs to get PST (avoids dealing with daylight savings times)
	df['Datetime'] = df['Collect Date (UTC)'] - timedelta(hours=8)

elif Agency == "USGS":
	# Convert to datetime64 format 
	df['Datetime'] = pd.to_datetime(df['Datetime'])

	# Round Datetime to the nearest 15 mins
	df['Datetime'] = df['Datetime'].dt.round('15min') 

	# Create new datetime64 column representing local time (including daylight savings effects) minus 1 hr
	df['LocalDT_Minus_1hr'] = df['Datetime'] - pd.Timedelta(hours=1) 

	# Update the Datetime column to shift daylight savings times (PDT) back to standard times
	# When Timezone col is PDT (daylight savings time), set Datetime col to LocalDT_Minus_1hr, otherwise keep value in Datetime col (this is PST)
	df['Datetime'] = np.where((df['Timezone'] == TimeZone), df['LocalDT_Minus_1hr'], df['Datetime'])

# Set the Datetime column as the index
df.set_index('Datetime', inplace=True)

# Create complete timeseries at each timestep, get first and last time stamps
start_time = df.index[0]
end_time = df.index[-1]

# Print read data for user verification
print("Check correct columns were read \nNote that daylight savings timestamps are shifted back 1-hr from the input data")
print("Timeseries start = {}".format(start_time.strftime('%Y-%m-%d %H:%M')))
print("Timeseries end = {}".format(end_time.strftime('%Y-%m-%d %H:%M')))
print("Gage value start = {:.1f}".format(df['Discharge'][0]))

# Create a complete timeseries with 15-min timestep and a new dataframe to store the complete, filled timeseries
# tz=None ensures this is timezone-naive
delta = timedelta(minutes=Timestep)
times = pd.date_range(start=start_time, end=end_time, freq=delta, tz=None)

# Create a new df from the timeseries
df_ts = pd.DataFrame(index=times)

# Determine number of missing records in the original timeseries
Num_missing = len(df_ts) - len(df)
print("Missing records: {}".format(Num_missing))

# Join the original gage data Dataframe (df) on index, leaves NaN where timestep is missing in original df
df_full = df_ts.join(df)

# Extract a new df of the original Datetime formatted Discharge rows with missing values
df_missing = df_full[df_full['Discharge'].isnull()]

# Remove duplicate timestamp values in the index
# This occurs when the gage sometimes reads out data like, for example, 06:14 and then 06:15, since we rounded timestamps to the nearest 15 mins above.
# Also occurs at the autumn changeover from PDT to PST, where there is a duplicate hour of records back to back.
df_full = df_full[~df_full.index.duplicated()]

# Drop unnecessary columns from the join
if Agency == "KC":
	df_full.drop(columns=['Site_Code','Collect Date (local)'], inplace=True)
elif Agency == "USGS":
	df_full.drop(columns=['Agency','Gage_ID','Notes'], inplace=True)

# Fill missing timesteps (currently saved as NaN) with '-901' 
df_full['Discharge'] = df_full['Discharge'].where(df_full['Discharge'].notnull(), -901)

# Create column which tracks sequential missing values of Discharge = -901 group size (how many -901's in a row)
df_full['Consec_Length'] = df_full['Discharge'].groupby(df_full['Discharge'].diff().ne(0).cumsum()).transform('size')

# Compute max allowable gap in missing timesteps for interpolation 
TS_gap = int(MaxGap/Timestep)

# Create flag to identify sections of missing data (-901) less than the max allowable gap 
df_full['Interp_Flag'] = np.where(((df_full['Discharge'] == -901) & (df_full['Consec_Length'] <= TS_gap)), 1, 0)

# Set Discharge = NaN for rows with Interp_Flag == 1 and Discharge == -901 
# Need to do this to enable interpolation in these rows (ie. can't interpolate on -901 because its treated as actual data)
df_full['Discharge'] = np.where(((df_full['Interp_Flag'] == 1) & (df_full['Discharge'] == -901)), np.nan, df_full['Discharge'])

# Interpolate on rows where Interp_Flag = 1 
print("Interpolating missing data in gaps less than {} timesteps".format(TS_gap))
df_full['Discharge'] = np.where((df_full['Interp_Flag'] == 1), df_full['Discharge'].interpolate(), df_full['Discharge'])
print("Filled records: {}".format(len(df_full[df_full['Interp_Flag'] == 1])))

# Quick check plot to verify interpolation looks good
f, ax = plt.subplots(figsize=(20,12))
ax.plot(df_full['Discharge'], label='Discharge')
ax.plot()
ax.legend()
#ax.grid()
ax.set_xlabel('Datetime')
ax.set_ylabel('Gage Value')
plt.savefig('gage_data.png', bbox_inches='tight')

# Make an interactive plot from a trimmed df with Pandas-Bokeh, save it out to html 
#pandas_bokeh.output_file("gage_plot.html")
#df_trim = df_full.drop(columns=['Consec_Length','Interp_Flag'])
#df_trim.plot_bokeh()

# Write final, filled data to file
print("Writing output file")
ColNames = ['Discharge']
fout = FileName[:-4]+'_filled.csv'
df_full.to_csv(fout, columns=ColNames, index_label='Datetime', date_format=DateFormat)

# Extract a new df of the rows where interpolation occurred (0 < Consec_Length < TS_gap)
df_interp = df_full[df_full['Interp_Flag'] == 1]

# Write summary of missing data & filled data
fn = FileName[:-4]+'_missing_interp_summary.csv'

# Setup the template for header above dataframe in csv, followed by 3 blank rows and then the dataframe
template1 = """\
Timesteps missing data:\n
{}"""

with open(fn, 'w') as f:
    f.write(template1.format(df_missing.to_csv(columns=ColNames, index_label='Datetime', date_format=DateFormat)))

template2 = """\
\nTimesteps interpolated:\n
{}"""    

with open(fn, 'a') as f:
    f.write(template2.format(df_interp.to_csv(columns=ColNames, index_label='Datetime', date_format=DateFormat)))

print("Filled gage data file: {}".format(fout))
print("Summary of missing and filled date/times: {}".format(fn))
print("Gage data plot: {}".format('gage_data.png'))