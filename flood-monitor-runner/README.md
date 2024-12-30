# Flood Monitoring Runner

This Docker container is designed to run the Flood Monitoring example project. It downloads time series forecasting models from a specified Edge Impulse project and runs them using live data from the Environment Agency API, plotting the results to images and serves them in a simple web server.

## Features

- Monitors flood data from various sources
- Configurable alert thresholds
- Easy to deploy using Docker

## Prerequisites

- Docker installed on your machine

## How to Run

1. Clone the repository:
    ```sh
    git clone https://github.com/yourusername/flood-monitoring-example-project.git
    cd flood-monitoring-example-project/flood-monitor-runner
    ```

2. Build the Docker image:
    ```sh
    docker build -t flood-monitor-runner .
    ```

3. Run the Docker container:
    ```sh
    docker run -p 80:80 flood-monitor-runner 
    ```
4. Access the results at:
    - [localhost/plot](http://localhost/plot) - to see the averaged result of all models and the historical readings of the predicted station and local rainfall
    - [localhost/plot_all](http://localhost/plot_all) - to see each individual model output and the historical readings of the predicted station and local rainfall 
    - [localhost/output.csv](http://localhost/output.csv) - to download the raw data of predictions and the historical readings of the predicted station and local rainfall


## Configuration

The `config.json` file is used to configure the behavior of the application. Below is an example of the `config.json` file and an explanation of each field:

```json
{
    "refresh_models_interval": 4,
    "models": [
        {"model": "modelfile_1hr.eim", "api": "APIKEY", "impulse-id": "36", "hours_ahead": 1},
        {"model": "modelfile_4hr.eim", "api": "APIKEY", "impulse-id": "2", "hours_ahead": 4},
        {"model": "modelfile_8hr.eim", "api": "APIKEY", "impulse-id": "71", "hours_ahead": 8},
        {"model": "modelfile_24hr.eim", "api": "APIKEY", "impulse-id": "3", "hours_ahead": 24}
    ],
    "foss_station_id": "F2470",
    "ref": "F2470",
    "rainfall_refs": ["059793"],
    "refs": ["F2470", "L2471", "L2472", "L2478"],
    "test_features": [0.0000, 0.6790, 7.6040, 5.1390, 0.2780, 0.0000, 0.6790, 7.6040, 5.1400, 0.2780, 0.0000, 0.6800, 7.6050, 5.1400, 0.2780, 0.0000, 0.6800, 7.6050, 5.1410, 0.2770, 0.0000, 0.6800, 7.6040, 5.1410, 0.2770, 0.0000, 0.6800, 7.6040, 5.1410, 0.2770]
}
```
### Fields

- `refresh_models_interval`: The interval (in runs) at which the models should be refreshed. Set to `-1` to never refresh.
- `models`: A list of models to be used by the application. Each model has the following fields:
  - `model`: The filename of the model.
  - `api`: The API key to download the model.
  - `impulse-id`: The impulse ID of the model.
  - `hours_ahead`: The number of hours ahead for the model.
- `foss_station_id`: The ID of the FOSS station.
- `ref`: The reference ID.
- `rainfall_refs`: A list of rainfall reference IDs.
- `refs`: A list of reference IDs.
- `test_features`: A list of test features.


You can pass the config file as an environment varaible with CONFIG_PATH e.g.
`docker run -e CONFIG_PATH='src/config.json' -p 80:80 flood-monitor`
## License

This project is licensed under the Apache 2.0 License. See the [LICENSE](../LICENSE) file for details.

