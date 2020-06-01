#!/home/cmeder/miniconda3/bin/python
# -*- coding: utf-8 -*-

"""
USGS_Gage_Fill_NoData_v1.py

This script fills gaps in discontinuous USGS gage data to create a continuous 
record. The user may specify a gap duration threshold below which the discharge 
values are linearly interpolated between starting and ending values. Longer 
duration gaps in the timeseries are filled with no data (i.e. '-901').   

This script has been modified to able to fill data other than USGS gage data.
The character that starts each line of data (which must not start a header line)
must be specified and the date format in the input file must be specified - it
will automatically output in date format '%Y-%m-%d %H:%M' but this can be edited. 
The delimeter (tab versus comma or other) must also be specified.

20200601 Updates (CCM)
- Print statements for Python 3
- Changed FirstCharacter to regex search for any digit, used for King County gage data
- Added tracking of timestamps with missing data and timestamps which were interpolated, write these to separate file for checking
- Added rounding of timestamps using func 'roundTime' to handle gage data with timestamps at values such as 00:14, 00:29, 00:44, 00:59

"""

import os
from datetime import datetime, timedelta
import numpy as np
import re # regex

# provide file information
#os.chdir(r'/mnt/c/Users/Chris.Meder/Egnyte/Private/chris.meder/Projects/20-008 Pacific Right Bank/Hydrology')
filename='usgs_12100496_12100490_combined_flow_record.txt'
Qcol = 5 # column containing discharge
TScol = 3 # column containing timestamp
timestep = 15 # in minutes
MaxGap = 180 # in minutes
FirstCharacter = 'U' # For USGS data, 'U'. Moved to regex search below, line 49
DateFormat = '%Y-%m-%d %H:%M' # For USGS data, '%Y-%m-%d %H:%M'. For KC data, '%m/%d/%Y %H:%M'.  %Y = 4-digit year, %y = 2-digit year
delimiter = '\t' # For USGS data, '\t'

# Function to round time to arbitrary timedelta
# Reference: https://stackoverflow.com/questions/3463930/how-to-round-the-minute-of-a-datetime-object/10854034#10854034
def roundTime(dt=None, roundTo=60):
   """Round a datetime object to any time lapse in seconds
   dt : datetime.datetime object, default now.
   roundTo : Closest number of seconds to round to, default 1 minute.
   Author: Thierry Husson 2012 - Use it as you want but don't blame me.
   """
   if dt == None : dt = datetime.datetime.now()
   seconds = (dt.replace(tzinfo=None) - dt.min).seconds
   rounding = (seconds+roundTo/2) // roundTo * roundTo
   return dt + timedelta(0,rounding-seconds,-dt.microsecond)

# create variables
date_str=[];
discharge=[];
dobj=[];

# Read in data
print("Start reading data from file {}".format(filename))
f=open(filename,'r')
a=f.readlines()
f.close()
for line in a:
    # For King County gages, uncomment next two lines, comment out 3rd line (if line[0]...)
    #FirstCharacter = re.search(r'^\d', line)
    #if FirstCharacter: 
    # Start reading data when the line starts with user-specified character
    if line[0] == FirstCharacter:
        try:
            discharge.append(float(line.split(delimiter)[Qcol-1]))
        except ValueError:
            discharge.append(-901)
        if line.split(delimiter)[TScol]=='PDT': #account for PDT/PST
            date_object=datetime.strptime(line.split(delimiter)[TScol-1], DateFormat)-timedelta(hours=1)
        else:
            date_object=datetime.strptime(line.split(delimiter)[TScol-1], DateFormat)            
        dobj.append(roundTime(date_object, roundTo=60*15))   # Added rounding to nearest 15 mins (CCM)
print("Finished reading data")       

# print data for check
st_time=dobj[0]   #datetime.strptime(date_str[0],'%Y-%m-%d %H:%M')
end_time=dobj[-1] #datetime.strptime(date_str[-1],'%Y-%m-%d %H:%M')
delta=timedelta(minutes=timestep)
print("Check correct columns were read...")
print("Timeseries start = {}".format(st_time))
print("Discharge start = {:.1f}".format(discharge[0]))

# create complete time series of 15 min (above) with no gaps
times=[]    
tobj=[]
while st_time < end_time:
    #times.append(st_time.strftime('%Y-%m-%d %H:%M'))
    #tobj.append(st_time)
    # Modified above two lines to round time to nearest 15 mins. Handles USGS gage data with values like (00:14, 00:29, 00:44, 00:59, etc) (CCM)
    times.append(roundTime(st_time, roundTo=60*15).strftime('%Y-%m-%d %H:%M'))
    tobj.append(roundTime(st_time, roundTo=60*15))
    st_time += delta

Num_missing = len(tobj)-len(dobj) # tobj = total records in complete timeseries, dobj = records found in the input file
print("{:d} total missing observations".format(Num_missing))    

# fill gaps - this looks for all time slots with no data and inserts -901
print("Start filling all gaps in timeseries (this takes a while)")  
n=0;
Q=[];    
times_missing=[];  
for i in range(len(times)):
    if dobj[n]==tobj[i]:
        Q.append(discharge[n])
        n=n+1;
    else:
        try:
            j=dobj.index(tobj[i])
        except ValueError:
             j=[]
        if j:
            Q.append(discharge[j])
            n=j+1
        else:
            Q.append(-901)
            times_missing.append(tobj[i]) # collect timestamps with missing data
    if 1*i/float(int(len(times)/10)) % 1 == 0:
        print("{:.1f} percent complete...".format((10*i/float(int(len(times)/10)))))
print("Finished filling gaps")     

#Interpolation routine- this looks for runs of 3hrs of -901
print("Start interpolating gaps in timeseries")
Qni=list(Q);
Qi=list(Q)
times_filled=[];
j=1
TS_gap=int(MaxGap/timestep)
s=0

while j:
    try:
        k=Q[j+1:].index(-901)
        j=j+k+1 # replace j 
        i=1
        while Q[j+i]==-901:
            i=i+1
        if i<=TS_gap: #if the gap in timeseries is less than or equal to max gap
                #interp lines
                Q[j:j+i]=np.interp(range(1,i+3),[1,i+2],[Q[j-1],Q[j+i]])[1:-1]
                for idx in range(j,j+i):
                    times_filled.append(tobj[idx])  # track starting date/time of interpolated gaps    
                j=j+i
                s=s+1
        else:
                j=j+i
    except ValueError:
        j=[]
        break  
print("Finished interpolation")   
print("{:.0f} gaps filled".format(s))

# Write File
f = open(filename[:-4]+'_filled.csv', 'wb')
for i in range(len(Q)): # xrange changed to range for Python 3
    f.write("{},{}\n".format(times[i],Q[i]).encode()) # .encode added for Python 3 compatibility
f.close()
print("File write complete ('{:s}_filled.csv')".format(filename[:-4]))     

# Write summary of gaps found and interpolated
f = open(filename[:-4]+'_times_missing.csv', 'wb')
f.write("Timesteps missing data:\n".encode())
for i in range(len(times_missing)): 
    f.write("{}\n".format(times_missing[i]).encode()) 

f.write("\nTimesteps interpolated:\n".encode())
for i in range(len(times_filled)):
    f.write("{}\n".format(times_filled[i]).encode())
f.close()