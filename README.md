Generation and simulation of time-series data from 
smart-meters (AC, Geyser, Overall) from 3 Houses
-----------------------------------------------------
- Note: The free web service on Render may respond slowly (~50 seconds) due to inactivity.

![Directory tree and diagram](server_data_homes/images/tree.png)

# Step-1: https://smart-home-backend-95to.onrender.com/stream_setup

   - Example API request (POST Method only):
     ```json
	{
	    "household": "B",
	    "interval": 5
	}
        ```

    - Example response:
        ```json
	{
	    "status": "Streaming setup successful"
	}
        ```
        
# Step-2: https://smart-home-backend-95to.onrender.com/stream_qstats

![Quick Stats from noise free data for outlier detection](server_data_homes/images/hist_stats.png)

# Step-3: https://smart-home-backend-95to.onrender.com/stream_data

![Server side updates after every interval seconds of average energy consumption in kW-min](server_data_homes/images/receiving_data.png)
     
# Data and Preprocessing

![Generating synthetic data of 1 second resolution both with or without noise](server_data_homes/images/gen_synthetic_data.png)

# Instructions for local installation and use

- Recommended Step-0: Create a virtual environment python -m venv venv

Activate it on Windows: venv\Scripts\activate Activate it on macOS and Linux: source venv/bin/activate

- Step-1. pip install -r requirements.txt

- Step-2. python3 app.py

Or build docker image and start it.

- docker build -t my_app .
- docker run -p 5000:5000 my_app

# Frontend

An android widget receiving updates from this live server showing time-series, changing colours according to events and allowing to take actions.

Webpage   :https://
GitHub    :
