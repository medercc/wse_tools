#!/usr/bin/env conda run -n gda python

"""
Python 3
Replaces Station/Elevation data in a HEC-RAS geometry file with linear referenced survey station/elevation data from a .csv file

Inputs:
1. A HEC-RAS geometry file (.g## format) with cross sections at the same river station locations as the linear referenced survey data 
   table (typically derived from ArcMap). This file should contain station/elevation data from terrain (LiDAR) cross section cuts, or
   perhaps old survey data.
2. A .csv formatted file containing linear referenced survey data at cross section river station locations in the HEC-RAS geometry file
	- The .csv header must currently use the following column names: 'River','Reach','RiverStation','MEAS','ELEV', where 'MEAS' and 'ELEV' 
      are the linear referenced station and elevation of the survey data.

Outputs:
1. A new HEC-RAS geometry file (nominally named with extension .g99) with the linear referenced survey data replacing the old 
   station/elevation data where river + reach + river station matches are found between the .g## and the .csv file. The first and last
   terrain sta/elev data points at each river station are maintained to appropriately locate the survey data. 

Chris Meder
5/24/2021

"""

# Include standard modules
import pandas as pd

# ---
# BEGIN USER INPUTS

# Read in RAS geometry file (.gXX format)
in_geom_file = 'Newaukum.g07'

# Set linear referenced data CSV filename 
lr_file = 'Newaukum_XSEC_for_SurfaceDevelopment_LinearReferencing.csv'

# END USER INPUTS
#---

# Flag to print debug output if needed (0=no, 1=yes)
debug = 0

# Columns to keep by name (the linear referencing .csv must use these column title names) 
# FUTURE: Add functionality to specify cols by number, then name them as below upon import
col_list = ('River','Reach','RiverStation','MEAS','ELEV')

# Read in the csv of linear referencing data
df = pd.read_csv(lr_file,usecols=col_list)
print("Reading survey data file: {}".format(lr_file))

# Sort the dataframe containing linear referencing
df_sort = df.sort_values(['River','Reach','RiverStation','MEAS'], ascending=[True, True, True, True])

# Group the dataframe by River, Reach and River Station, then count number of points at each River Station and store it
df_grouped = df.groupby(['River','Reach','RiverStation']).size().reset_index(name="NumPoints")

# Set new filename for writing output, create the file
out_geom_file = in_geom_file[:-4]+'.g99'

# Open the original geometry file and read it into an array 
print("Reading HEC-RAS geometry file: {}".format(in_geom_file))
with open(in_geom_file) as f:
    farray = f.readlines()

# Open the new geometry file for writing the output
fout = open(out_geom_file, "w")

# Declare some markers to track progress through the file
riv_rch_found = 0 # River Reach
rs_found = 0 # River Station
sta_elev_found = 0 # Station Elevation
        
# Loop over each line of the geometry file array, searching for unique River, Reach & River Station combinations (ie a unique RS)
for num, line in enumerate(farray):
    
    # Add a descriptor to the 'Geom Title' in the first line of the file
    if (num == 0):
        fout.write(farray[0][:-1] + "_WithSurvey\n")
    
    # If this is the section of Sta/Elev data, skip writing lines until the end of the section
    if ((sta_elev_found == 1) & ("#Mann" not in line)):
        # Skip to the next line
        next
        
    # Sta/Elev ends when the #Mann line is encountered. Write the survey data in before writing the #Mann line and moving on   
    if (sta_elev_found == 1) & ('#Mann=' in line):
        
        # Grab the previous line in the file array (last line of the old sta elev data), extract the last point 
        # pair (16 chars), and it to the new sta elev point array
        last_line = farray[num-1]
        last_point = last_line[-17:]
        pt_array.append(last_point)
                
        # Write out the new sta elev data from the point array (80 chars per line)
        pt_string = ""
        for n, p in enumerate(pt_array, start=1):
            
            # Add the current pt to the string
            pt_string += p    
                    
            # Check the length of the pt string...
            # When the pt string reaches 80 chars, write it out and start a new line
            if len(pt_string) == 80:
                fout.write("{}\n".format(pt_string))                        
                # Reset pt_string
                pt_string = ""
                    
            # Keep adding pts to the string until string is 80 characters long
            elif ((len(pt_string) < 80) & (n < len(pt_array))):
                # Go to the next pt and add it to the pt string
                next
                        
            # If this is the last point in the array and we haven't hit 80 characters yet, write it out and move on    
            else:
                fout.write("{}".format(pt_string))
             
        # Reset some flags
        rs_found = 0 # River Station
        sta_elev_found = 0 # Station Elevation

        # Skip to the next line in farray
        next
        
    # Search for "River Reach=" line    
    if ("River Reach=" in line):
        
        # Search the grouped dataframe for a River + Reach match
        for row in df_grouped.itertuples():
            
            # Set search strings from the row in the grouped dataframe
            # River + Reach (fixed field 16 characters)
            riv_fm = '{:<16},'.format(row.River)
            riv_rch_string = "River Reach=" + riv_fm + row.Reach
            # River Station (fixed field 8 characters)
            rs_string = ',{:<8}'.format(row.RiverStation)
            
            # If River, Reach is found in the grouped dataframe, set flag to search for the River Station next
            if riv_rch_string in line:
                riv_rch_found = 1
                if (debug):
                	print("\nFound River Reach Match: {} {}\n------------------".format(row.River, row.Reach))
                # Break out of the grouped dataframe for loop search
                break
                
    # When River + Reach is located, search for River Station (RS) in a successive line     
    if ((riv_rch_found == 1) & ("Type RM" in line)):
                    
        # Grab a subset of the grouped dataframe for the current River + Reach 
        if (debug): 
           	print("Getting grouped data for: {} {}".format(row.River, row.Reach))
        
        df_riv_rch = df_grouped[(df_grouped.River == row.River) & (df_grouped.Reach == row.Reach)]
        
        # Check each River Station in the subset dataframe
        for rs in df_riv_rch.itertuples():
            rs_string = ',{:<8}'.format(rs.RiverStation)
            
            # If the River Station matches what's in line, set the flag
            if ((rs_string in line)):
                rs_found = 1
                print("Found River Station match: {}, {}, {}".format(rs.River, rs.Reach, rs.RiverStation))
                break
                    
    # When the current River Station is located, find the #Sta/Elev line and set a flag
    if ((riv_rch_found == 1) & (rs_found == 1) & ("#Sta/Elev=" in line)):
        sta_elev_found = 1
        
        # Replace the number of Sta/Elev points in the line with NumPoints from the grouped dataframe, +2 to account 
        # for first and last taken from existing data
        fout.write('#Sta/Elev= {}\n'.format(rs.NumPoints+2))

        # Get the subset of the linear referenced dataframe for the current River, Reach, River Station combination
        if (debug):
        	print("Getting survey for: {} {} {}".format(rs.River, rs.Reach, rs.RiverStation))
        
        df_rs = df_sort[(df_sort.River == rs.River) & (df_sort.Reach == rs.Reach) & (df_sort.RiverStation == rs.RiverStation)]

        # Cycle over the rows of the subset linear referenced dataframe (already sorted), extract MEAS and ELEV and save in an array 
        # to replace the station elevation points in the geom file
        pt_array = []
        for pt in df_rs.itertuples():
            pt_array.append('{:8.3f}'.format(pt.MEAS)+'{:8.3f}'.format(pt.ELEV))  

        # Grab the next line in the file array (first line of the sta elev data), extract the first 
        # point pair (16 chars), add it to the front of the new sta elev point array
        first_line = farray[num+1]
        first_point = first_line[0:16]
        pt_array.insert(0, first_point)
        
        # Skip to the next line in farray
        next

    # Write all other lines to outfile, unless this is the first line in the file or the Sta/Elev data chunk
    elif ((num != 0) & (sta_elev_found != 1)):
        # Write the line to the new outfile
        fout.write(line)

# Close the output filehandle
fout.close()         

print("New geometry file with survey is: {}".format(out_geom_file))