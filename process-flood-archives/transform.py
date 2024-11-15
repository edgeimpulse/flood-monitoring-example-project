
import os, argparse, requests
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from datetime import datetime, timedelta

# these are the three arguments that we get in
parser = argparse.ArgumentParser(description='Organization transformation block')
parser.add_argument('--in-directory', type=str, required=True)
parser.add_argument('--out-directory', type=str, required=True)
parser.add_argument('--start-date', type=int, required=True)
parser.add_argument('--end-date', type=int, required=True)
parser.add_argument('--label-station', type=str, required=True)
parser.add_argument('--flood-stations', type=str, required=True)
parser.add_argument('--rain-stations', type=str, required=True)
parser.add_argument('--normal-limit', type=float, required=True)
parser.add_argument('--high-limit', type=float, required=True)
parser.add_argument('--flood-limit', type=float, required=True)
parser.add_argument('--deltas', type=str, required=True)
parser.add_argument('--split', type=int, required=True)
args, unknown = parser.parse_known_args()


# Calculate the dates for the past year
end_date = datetime.now() - timedelta(days=args.end_date)
start_date = end_date - timedelta(days=args.start_date)
ref = args.label_station
rainfall_refs = args.rain_stations.split(',')
refs = args.flood_stations.split(',')
refs = refs + rainfall_refs
input_folder = args.in_directory
output_folder = args.out_directory
normal = args.normal_limit
high = args.high_limit
flood = args.flood_limit
deltas = [float(x) for x in args.deltas.split(',')]

if not os.path.exists(args.in_directory):
    print("Input directory does not exist")
    exit(1)

if not os.path.exists(args.out_directory):
    os.makedirs(args.out_directory)
if not os.path.exists(os.path.join(output_folder,ref, 'processed')):
    os.makedirs(os.path.join(output_folder,ref,'processed'))
if not os.path.exists(os.path.join(output_folder,ref, f'combined_{args.split}hr_split')):
    os.makedirs(os.path.join(output_folder,ref,f'combined_{args.split}hr_split'))

def download_and_process(date_str):
    csv_file_path = os.path.join(input_folder, f'readings_{date_str}.csv')
    output_file = os.path.join(output_folder,ref,'processed', f'readings_{date_str}_{ref}.csv')

    if os.path.exists(output_file):
        print(f"File {output_file} already exists, skipping...")
        return
    if not os.path.exists(csv_file_path):
        print(f"File {csv_file_path} doesn't exist, skipping...")
        return

    # Load the data from the CSV file
    df = pd.read_csv(csv_file_path, usecols=['dateTime', 'value', 'stationReference'])

    # Filter the data for the station references in refs
    df_filtered = df[df['stationReference'].isin(refs)]

    # Convert the value column to numeric, forcing errors to NaN
    df_filtered['value'] = pd.to_numeric(df_filtered['value'], errors='coerce')

    # Drop rows with NaN values in the value column
    df_filtered = df_filtered.dropna(subset=['value'])

    # Pivot the data to have columns for each station reference
    df_pivoted = df_filtered.pivot(index='dateTime', columns='stationReference', values='value')

    # Convert dateTime column to datetime format
    df_pivoted.index = pd.to_datetime(df_pivoted.index)

    # Sort dateTime index in ascending order to ensure the data is in chronological order
    df_pivoted = df_pivoted.sort_index()

    # Resample the data to ensure all dateTimes are aligned, filling missing values with NaN
    df_resampled = df_pivoted.resample('15T').asfreq()
    

    # Save the resampled data to a new CSV file
    df_resampled.to_csv(output_file, index=True)
    print(f"Filtered data saved to {output_file}")

# Create a list of date strings for the past year
date_list = [(start_date + timedelta(days=x)).strftime('%Y-%m-%d') for x in range((end_date - start_date).days + 1)]

# Use ThreadPoolExecutor to download and process files concurrently
with ThreadPoolExecutor(max_workers=10) as executor:
    executor.map(download_and_process, date_list)

print("Download and processing complete.")
combined_csv_file = f'{ref}_combined_output.csv'

# List to hold dataframes
dfs = []


# Iterate through the files in the output folder
for file_name in os.listdir(os.path.join(output_folder,ref,'processed')):
    if file_name.endswith('.csv'):
        file_path = os.path.join(output_folder,ref,'processed', file_name)
        # Load the data from the CSV file
        df = pd.read_csv(file_path)
        dfs.append(df)


# Concatenate all dataframes
combined_df = pd.concat(dfs)
# add a new column with labels for low, normal and flood levels based on the value column, using the normal and flood thresholds
combined_df['level'] = pd.cut(combined_df[ref], bins=[-1, normal, high, flood, 100], labels=['low', 'normal','high', 'flood'])

# remove duplicate rows from dateTime column
combined_df = combined_df.drop_duplicates('dateTime')
# Convert dateTime column to datetime format
combined_df['dateTime'] = pd.to_datetime(combined_df['dateTime'])

# Sort the combined dataframe by dateTime in chronological order
combined_df = combined_df.sort_values('dateTime')
# Ensure that the dateTime column is in 15-minute increments, if a row is missing interpolate between the two surrounding rows
combined_df = combined_df.set_index('dateTime').resample('15T').asfreq()
# Interpolate missing values in the refs columns using linear interpolation
for refr in refs:
    if refr not in rainfall_refs:
        # replace 0 values with NaN
        combined_df[refr] = combined_df[refr].where(combined_df[refr] != 0, pd.NA)
    combined_df[refr] = combined_df[refr].interpolate(method='linear')
    if combined_df[refr].isna().sum() > 0:
        # if there are still Nan FFill the remaining values
        combined_df[refr] = combined_df[refr].bfill()
        combined_df[refr] = combined_df[refr].ffill()

    print(f"Number of NaN values in {refr}: {combined_df[refr].isna().sum()}")

# add columns for the deltas (15, 30, 60, 120 minutes) which are the the ref column shifted by the delta/15 minutes
for delta in deltas:
    combined_df[f'{ref}_{delta}h'] = combined_df[ref].shift(-int(delta/0.25))
    combined_df[f'{ref}_{delta}h'] = combined_df[f'{ref}_{delta}h'].bfill()

# add a column which encodes the season as a number (0 for winter [December, January, February], 1 for spring [March, April, May], 2 for summer [June, July, August], 3 for autumn [September, October, November])
combined_df['season'] = combined_df.index.month % 12 // 3

if args.split > 0:
    # Split combined dataframe into n hour chunks and save to separate CSV files
    n = args.split
    for i in range(0, len(combined_df), n*4):
        chunk_df = combined_df.iloc[i:i+n*4]    
        start_datetime = chunk_df.index[0].strftime('%Y%m%d%H%M%S')
        end_datetime = chunk_df.index[-1].strftime('%Y%m%d%H%M%S')
        chunk_df.to_csv(os.path.join(output_folder,ref,f'combined_{args.split}hr_split',f'{ref}_{start_datetime}_to_{end_datetime}.csv'))
    print(f"Combined data split into {len(combined_df)//(n*4)} chunks.")

else:
    # Save the combined dataframe to a new CSV file
    combined_df.to_csv(os.path.join(output_folder,ref,f'combined_{args.split}hr_split',combined_csv_file))

print("Combining complete.")