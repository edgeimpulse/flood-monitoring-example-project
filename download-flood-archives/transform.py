
import os, argparse, requests
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

# these are the three arguments that we get in
parser = argparse.ArgumentParser(description='Organization transformation block')
parser.add_argument('--out-directory', type=str, required=True)
parser.add_argument('--start-date', type=int, required=True)
parser.add_argument('--end-date', type=int, required=True)
args, unknown = parser.parse_known_args()

if not os.path.exists(args.out_directory):
    os.makedirs(args.out_directory)

# Calculate the dates for the past year
end_date = datetime.now() - timedelta(days=args.end_date)
start_date = end_date - timedelta(days=args.start_date)

def download_and_process(date_str):
    url = f'http://environment.data.gov.uk/flood-monitoring/archive/readings-full-{date_str}.csv'
    csv_file_path = os.path.join(args.out_directory, f'readings_{date_str}.csv')

    if os.path.exists(csv_file_path):
        print(f"Data for {date_str} already exists.")
        return

    # Download the CSV file
    response = requests.get(url)
    if response.status_code == 200:
        with open(csv_file_path, 'wb') as file:
            file.write(response.content)
        print(f"Downloaded {csv_file_path}")
    else:
        print(f"Failed to download data for {date_str}")
        return

# Create a list of date strings for the past year
date_list = [(start_date + timedelta(days=x)).strftime('%Y-%m-%d') for x in range((end_date - start_date).days + 1)]

# Use ThreadPoolExecutor to download and process files concurrently
with ThreadPoolExecutor(max_workers=10) as executor:
    executor.map(download_and_process, date_list)

print("Download and processing complete.")
