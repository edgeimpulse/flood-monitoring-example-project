import os
from edge_impulse_linux.runner import ImpulseRunner
import requests
import pandas as pd
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib
import json
matplotlib.use('Agg')
#add an ENV variable for config file path
path = os.getenv('CONFIG_PATH', 'src/config.json')

def load_config(path):
    # Load configuration from config.json
    with open(path, 'r') as config_file:
        config = json.load(config_file)
    return config

def main():
    run_counter = 0

    config = load_config(path)
    # Load refresh models flag from environment variable as an int (every N runs the models will be refreshed, -1 for never)
    refresh_models = int(config['refresh_models_interval'])
    models = config['models']
    ref = config['ref']
    rainfall_refs = config['rainfall_refs']
    refs = config['refs']
    test_features = config['test_features']

    

    # init all model runners
    for model in models:
        # Refresh models based on the counter and refresh_models value
        if not os.path.isfile(model['model']) or (refresh_models != -1 and run_counter % refresh_models == 0):
            print('Downloading model ' + model['model'])
            os.system('edge-impulse-linux-runner --api-key ' + model['api'] + ' --download ' + model['model']+ ' --impulse-id '+model['impulse-id'])
    # Use the current working directory instead of __file__
        dir_path = os.getcwd()
        modelfile = os.path.join(dir_path, model['model'])
        
        try:
            model['runner'] = ImpulseRunner(modelfile)
            model['info'] = model['runner'].init()
            print('Loaded runner for "' + model['info']['project']['owner'] + ' / ' + model['info']['project']['name'] + '"')
        except Exception as e:
            print(f"Error initializing runner for model {model['model']}: {e}")
            continue  # Skip this model if initialization failed

    run_counter += 1
    # classify all models
    for model in models:
        try:
            res = model['runner'].classify(test_features)
            print('Model ' + model['model'] + ' classified the features as ' + str(res['result']['classification']['value']))
        except Exception as e:
            print(f"Error classifying features with model {model['model']}: {e}")
            continue



    refs = rainfall_refs + refs
    # Initialize an empty DataFrame to store all readings
    combined_df = pd.DataFrame()
    for stations in refs:
        url = f'https://environment.data.gov.uk/flood-monitoring/id/stations/{stations}/readings?_sorted'
        response = requests.get(url)
        data = response.json()
        readings = data['items']
        # Create a DataFrame for the current station's readings
        station_df = pd.DataFrame(readings)
        # drop '@id', 'measure' columns and rename 'value' to station
        station_df.drop(columns=['@id', 'measure'], inplace=True)
        station_df.rename(columns={'value': stations}, inplace=True)
        # set the index to the 'dateTime' column
        station_df.set_index('dateTime', inplace=True)
        # Append the station's readings to the all_readings_df DataFrame matching the index
        combined_df = pd.concat([combined_df, station_df], axis=1)

    #sort the index in ascending order
    combined_df.sort_index(inplace=True)
    print(f'Last reading found at {combined_df.index[-1]}')
    for refr in refs:
        if refr not in rainfall_refs:
            # replace 0 values with NaN
            combined_df[refr] = combined_df[refr].where(combined_df[refr] != 0, pd.NA)
        combined_df[refr] = combined_df[refr].interpolate(method='linear')
        if combined_df[refr].isna().sum() > 0:
            # if there are still Nan FFill the remaining values
            combined_df[refr] = combined_df[refr].bfill()
            combined_df[refr] = combined_df[refr].ffill()

    # add a column which encodes the season as a number (0 for winter [December, January, February], 1 for spring [March, April, May], 2 for summer [June, July, August], 3 for autumn [September, October, November])
    # Use the current month to determine the season
    current_month = pd.Timestamp.now().month
    combined_df['season'] = current_month % 12 // 3

    # add columns for the deltas (15, 30, 60, 120 minutes) which are the the ref column shifted by the delta/15 minutes
    for model in models:
        delta = model['hours_ahead']
        combined_df[f'{ref}_{delta}h'] = combined_df[ref].shift(-int(delta/0.25))
        combined_df[f'{ref}_{delta}h'] = combined_df[f'{ref}_{delta}h'].bfill()
    # Display the DataFrame


    window_length = 5400000 #ms
    rows = int(window_length/900000) # 15 minutes

    # create a copy of combined_df with only index and ref columns
    output_df = combined_df[[ref, '059793']].copy()
    # format index as datetime
    output_df.index = pd.to_datetime(output_df.index)

    # Create a DataFrame with 24 hours more rows, leaving all rows empty
    additional_rows = pd.DataFrame(
        pd.NA, 
        index=pd.date_range(start=output_df.index[-1] + pd.Timedelta(minutes=15), periods=int(24/0.25), freq='15T'), 
        columns=output_df.columns
    )

    # Concatenate the original DataFrame with the additional rows
    output_df = pd.concat([output_df, additional_rows])

    # Take 30 rows at a time with an increase of 1 row, and classify the features for each model- storing the results in columns in the combined_df
    for i in range(0, len(combined_df)-rows):
        # Get rows from the combined_df for only the columns in refs
        features = combined_df.loc[combined_df.index[i:i+rows], refs+['season']].values.flatten().tolist()

        # skip if features contains nan
        if any(pd.isna(features)):
            continue
        for model in models:
            res = model['runner'].classify(features)
            rows_delta = int(model['hours_ahead']/0.25)
            classification_value = res['result']['classification']['value']
            # output_df.at[output_df.index[i+rows+rows_delta], f'{model["model"][:-4]}_classified'] = str(classification_value)
            output_df.at[output_df.index[i], f'{model["model"][:-4]}_classified'] = str(classification_value)

    for model in models:
        delta = model['hours_ahead']
        output_df[f'{model["model"][:-4]}_classified'] = output_df[f'{model["model"][:-4]}_classified'].shift(int(delta/0.25)+rows)
        output_df[f'{model["model"][:-4]}_classified'] = output_df[f'{model["model"][:-4]}_classified'].bfill()


    #save to csv with index column names as dateTime
    output_df.index.name = 'dateTime'
    output_df.to_csv('output.csv', index=True)


    output_df_2 = output_df.copy()


    # Define a custom rolling function that ignores zero values
    def rolling_mean_ignore_zeros(series, window):
        return series.rolling(window=window).apply(lambda x: x[x != 0].mean(), raw=False)

    # Apply the custom rolling function to each classified column
    output_df_2['modelfile_1hr_classified'] = rolling_mean_ignore_zeros(output_df_2['modelfile_1hr_classified'], window=20)
    output_df_2['modelfile_4hr_classified'] = rolling_mean_ignore_zeros(output_df_2['modelfile_4hr_classified'], window=20)
    output_df_2['modelfile_8hr_classified'] = rolling_mean_ignore_zeros(output_df_2['modelfile_8hr_classified'], window=20)
    output_df_2['modelfile_24hr_classified'] = rolling_mean_ignore_zeros(output_df_2['modelfile_24hr_classified'], window=20)

    # replace 0 values with NaN
    output_df_2['modelfile_1hr_classified'] = output_df_2['modelfile_1hr_classified'].where(output_df_2['modelfile_1hr_classified'] != 0, pd.NA)
    output_df_2['modelfile_4hr_classified'] = output_df_2['modelfile_4hr_classified'].where(output_df_2['modelfile_4hr_classified'] != 0, pd.NA)
    output_df_2['modelfile_8hr_classified'] = output_df_2['modelfile_8hr_classified'].where(output_df_2['modelfile_8hr_classified'] != 0, pd.NA)
    output_df_2['modelfile_24hr_classified'] = output_df_2['modelfile_24hr_classified'].where(output_df_2['modelfile_24hr_classified'] != 0, pd.NA)
    # do the same for f2470
    output_df_2['F2470'] = output_df_2['F2470'].where(output_df_2['F2470'] != 0, pd.NA)

    #add an averaged column which is the average of the 3 classified columns (ignoring Nan values)
    output_df_2['average'] = output_df_2[['modelfile_1hr_classified', 'modelfile_4hr_classified','modelfile_8hr_classified','modelfile_24hr_classified', 'F2470']].mean(axis=1)
    output_df_2['average'] = output_df_2['average'].rolling(window=20).median()

    # save to csv with only dateTime and average columns, 
    output_df_2.index.name = 'dateTime'
    output_df_2[['average']].to_csv('output_2.csv', index=True)



    # Plot the data
    fig, ax = plt.subplots(figsize=(20, 10))

    # Plot each column with a different color and handle NaN values by filling them with 0
    ax.plot(output_df.index, output_df_2['F2470'], label='F2470', color='blue', linestyle='-', marker='o', markersize=2)
    ax.plot(output_df.index, output_df['059793'], label='059793', color='blue', linestyle='-', marker='o', markersize=2)

    # ax.plot(output_df.index, output_df_2['modelfile_1hr_classified'], label='modelfile_1hr_classified', color='green', linestyle='-', marker='o', markersize=2)
    # ax.plot(output_df.index, output_df_2['modelfile_4hr_classified'], label='modelfile_4hr_classified', color='red', linestyle='-', marker='o', markersize=2)
    # ax.plot(output_df.index, output_df_2['modelfile_8hr_classified'], label='modelfile_8hr_classified', color='black', linestyle='-', marker='o', markersize=2)
    # ax.plot(output_df.index, output_df_2['modelfile_24hr_classified'], label='modelfile_24hr_classified', color='purple', linestyle='-', marker='o', markersize=2)
    ax.plot(output_df.index, output_df_2['average'], label='average', color='grey', linestyle='-', marker='o', markersize=2)


    # Set the x-axis to display hours and minutes
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=4))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %H:%M'))

    # Rotate x-axis labels for better readability
    plt.xticks(rotation=45)

    #set y axis limits from 0 to 3
    plt.ylim(0, 3)

    #set x axis limits to the last 24 hours
    plt.xlim(pd.Timestamp.now() - pd.Timedelta(hours=24*4), pd.Timestamp.now()+ pd.Timedelta(hours=16))
    #add a line at y=2.2 and label with "Top of normal range"
    plt.axhline(y=2.2, color='r', linestyle='--', label='Top of normal range')

    # add a vertical line for the current time
    plt.axvline(x=pd.Timestamp.now(), color='black', linestyle='--', label='Current time')
    # Add legend to the plot
    plt.legend()
    #check if path exists
    if not os.path.exists('static'):
        os.makedirs('static')
    # Save the plot to a file
    plt.savefig('static/plot.png')
    plt.close()
    print('Plot saved to static/plot.png')
    # Plot the data
    fig, ax = plt.subplots(figsize=(20, 10))

    # Plot each column with a different color and handle NaN values by filling them with 0
    ax.plot(output_df.index, output_df_2['F2470'], label='F2470', color='blue', linestyle='-', marker='o', markersize=2)
    ax.plot(output_df.index, output_df['059793'], label='059793', color='blue', linestyle='-', marker='o', markersize=2)

    ax.plot(output_df.index, output_df_2['modelfile_1hr_classified'], label='modelfile_1hr_classified', color='green', linestyle='-', marker='o', markersize=2)
    ax.plot(output_df.index, output_df_2['modelfile_4hr_classified'], label='modelfile_4hr_classified', color='red', linestyle='-', marker='o', markersize=2)
    ax.plot(output_df.index, output_df_2['modelfile_8hr_classified'], label='modelfile_8hr_classified', color='black', linestyle='-', marker='o', markersize=2)
    ax.plot(output_df.index, output_df_2['modelfile_24hr_classified'], label='modelfile_24hr_classified', color='purple', linestyle='-', marker='o', markersize=2)
    ax.plot(output_df.index, output_df_2['average'], label='average', color='grey', linestyle='-', marker='o', markersize=2)


    # Set the x-axis to display hours and minutes
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=4))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %H:%M'))

    # Rotate x-axis labels for better readability
    plt.xticks(rotation=45)

    #set y axis limits from 0 to 3
    plt.ylim(0, 3)

    #set x axis limits to the last 24 hours
    plt.xlim(pd.Timestamp.now() - pd.Timedelta(hours=24*4), pd.Timestamp.now()+ pd.Timedelta(hours=16))
    #add a line at y=2.2 and label with "Top of normal range"
    plt.axhline(y=2.2, color='r', linestyle='--', label='Top of normal range')

    # add a vertical line for the current time
    plt.axvline(x=pd.Timestamp.now(), color='black', linestyle='--', label='Current time')
    # Add legend to the plot
    plt.legend()
    #check if path exists
    if not os.path.exists('static'):
        os.makedirs('static')
    # Save the plot to a file
    plt.savefig('static/plot_all.png')
    plt.close()
    print('Plot saved to static/plot_all.png')
    #print date
    print(pd.Timestamp.now())
if __name__ == '__main__':
    main()