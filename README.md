# Flood Monitoring Data Transformation Blocks

This project contains a set of transformation blocks designed to work with the UK Government River Level and Rainfall Data API. The purpose of these blocks is to download and process the last two years' worth of flood and rain data from across the country. The data is then narrowed down to a series of defined flood monitoring stations and rainfall monitoring stations, combined into a single dataset, and prepared for training a machine learning model to predict future river levels up to twenty-four hours ahead based on previous data.

## Transformation Blocks

### 1. Download Flood Archives

This transformation block downloads the archive flood and rain data from the UK Government River Level and Rainfall Data API. It retrieves data for the last two years and stores it in a specified output directory. The block ensures that only new files are downloaded if they are present.

**File:** [download-flood-archives/transform.py](download-flood-archives/transform.py)

**Parameters:**
- `out-directory`: The directory where the raw data will be saved.
- `start-date`: The start date (relative to today) in days.
- `end-date`: The end date (relative to today) in days.

### 2. Process Flood Archives

This transformation block processes the downloaded flood and rain data archives. It narrows down the data to a series of defined flood monitoring stations and rainfall monitoring stations. The block then combines the data into a single dataset, which can be used for training a machine learning model to predict future river levels.

**File:** [process-flood-archives/transform.py](process-flood-archives/transform.py)

**Parameters:**
- `in-directory`: The directory where the raw data is stored.
- `out-directory`: The directory where the processed data will be saved.
- `label-station`: The station used for labeling.
- `rain-stations`: Comma-separated list of rainfall monitoring stations.
- `flood-stations`: Comma-separated list of flood monitoring stations.
- `normal-limit`: The threshold for normal river levels.
- `high-limit`: The threshold for high river levels.
- `flood-limit`: The threshold for flood river levels.
- `deltas`: Comma-separated list of time deltas for prediction. e.g "0.5, 1,2,4,8,12,24,48"

## Usage

 1. **Download Flood Archives:**

   Use the `download-flood-archives` transformation block to download the last two years' worth of flood and rain data.

   ```python
   python download-flood-archives/transform.py --out-directory <output_directory> --start-date 730 --end-date 0
   ```
 2. **Process Flood Archives:**

Use the process-flood-archives transformation block to process the downloaded data and combine it into a single dataset.


 3. **Train a Machine Learning Model**

To train a machine learning model using the combined dataset, follow these steps:

**Configure CSV Wizard:**

   Use the CSV Wizard configuration tool to set up your training data. Take a single CSV file from your processed data (the output from process-flood-archives), and upload this into the [CSV Wizard](https://docs.edgeimpulse.com/docs/edge-impulse-studio/data-acquisition/csv-wizard) in a new Edge Impulse project.  Specify the label column and the data columns that you want to use for training your model. 

   - **Label Column:** This is the column that contains the target variable you want to predict (e.g., future river levels) E.G. F2470_1hr as your label column will allow you to train a regression model that can forecast 1 hour ahead
   - **Data Columns:** These are the columns that contain the input features for your model (e.g., rainfall data, river levels). This should not include your time delta columns, just the raw data columns.

**Import Your Processed Data:**

   Once the Wizard is configured you can import all of your processed data. If this is on your desktop then simply upload the files using the Data Acquisition web upload tool. If you have used the transformation blocks inside an Organisation you can import your data directly from the Dataset your transformation block outputted to. To achieve this head to Data Acquisition->Data Sources and choose the Dataset and relevant path (e.g. "flood-monitoring/F2470/combined_48hr_split/"). This method can be set up as an automatic pipeline which monitors the dataset for any new data and then ingests it into your project, retraining and deploying a new version.

**Split your data for Training & Testing:**
    
   When performing time series forecasting, it is crucial to split your data into training and testing sets based on a date to ensure that the model is evaluated on its ability to predict future values rather than simply memorizing past data. By separating the data such that the training set consists of data from one period (e.g., one year) and the testing set from a subsequent period (e.g., the following year), you prevent data leakage, where information from the future could inadvertently influence the model during training. 

   The simplest way to do this is to make use of the filtering tools in the Data Acquisition screen. Filter the filenames by e.g. "2023" and move all those samples to the testing set, then filter the testing set by "2024" and move all those samples to the training set. This will make sure you are validating this model based on unseen data. 

**Train the Model:**

   Once the CSV Wizard is configured, proceed with training your machine learning model using the specified label and data columns. As this is very low frequency data, you'll need to set your window size and increase to a very large millisecond value such as 5400000ms (1.5 hours). 

**Evaluate the Model:**

   After training, evaluate the performance of your model using appropriate metrics (e.g., mean absolute error, root mean squared error) to ensure it accurately predicts future river levels.

**Deploy the Model:**

   Once you are satisfied with the model's performance, deploy it to make real-time predictions based on new input data. The input data could be scraped from the [Environment Agency Real Time Data API](https://environment.data.gov.uk/flood-monitoring/doc/reference) and passed directly into the model. You could chain multiple time-delta trained models together to get a longer forecast, the shorter the time delta the higher accuracy your model is likely to be so this is important to bare in mind. If river level is influenced by rainfall, the +1Hr model is more likely to respond accurately to the input rainfall than the +24hr model. 

   These models could be run in bare metal on an MCU *or* on a linux MPU as they have low compute requirements. Running on Linux would allow more flexibility for OTA updating of the models when new versions are available.

   The [flood-monitor-runner] folder contains an example docker container which will download the most recent model files and run your models every 15 minutes outputting to images which are hosted in a simple webpage. This could be run on an MPU like a Raspberry Pi.

By following these steps, you can effectively train a machine learning model to predict future river levels using the processed flood and rain data.

## Output
The final output is a combined dataset containing the processed flood and rain data for the defined monitoring stations. This dataset can be used to train a machine learning model to predict future river levels up to twenty-four hours ahead based on previous data.

## License
This project is licensed under the Apache License 2.0. See the LICENSE file for details.

## Data Source License

The download block makes use of the Environment Agency Real Time Data API, which is licensed under the [Open Government License v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).
