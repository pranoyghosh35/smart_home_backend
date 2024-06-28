"""
This module simulates averaged energy consumption data from synthetic 1-second resolution
energy consumption data in kW-min (kilowatt-minute). It provides endpoints to set up streaming
parameters, stream averaged household data using Server-Sent Events (SSE), and compute statistics
such as median, standard deviation, and critical values for a given household.

Note: 1 kW-min = 60 kJ (kilojoules)
"""

from flask import Flask, request, Response, jsonify
import pandas as pd
import numpy as np
import time
import json
from scipy import stats

app = Flask(__name__)

# Load the dataset
data = pd.read_csv('server_data_homes/realistic_fake_energy_data_with_errors.csv', low_memory=False)

# Load clean dataset as historical data for stats, outliers
tmp = pd.read_csv('server_data_homes/realistic_fake_energy_data_without_errors.csv')

# Global variables to store household and interval
current_household = None
current_interval = None

def get_household_data(df, household):
    """
    Retrieves household-specific data from a DataFrame.

    Parameters:
    - df (pd.DataFrame): The DataFrame containing household data.
    - household (str): The identifier for the household (e.g., 'A', 'B', 'C').

    Returns:
    - pd.DataFrame: Filtered DataFrame with columns for AC, Geyser, Overall.
    """
    household_data = df[[f"{household}_AC", f"{household}_Geyser", f"{household}_Overall"]]
    household_data.columns = ['AC', 'Geyser', 'Overall']
    return household_data

def stream_data(index):
    """
    Generator function to stream averaged household data.

    Yields:
    - str: JSON-formatted string containing average values of AC, Geyser, Overall.
    """
    global current_household, current_interval
    household_data = get_household_data(data, current_household)
    num_rows = len(household_data)
    start_index = index
    end_index = start_index + current_interval
    while True:
        recent_data = household_data.iloc[start_index:end_index]
        try:
            average_values = recent_data.astype(float).mean().round(3).to_dict()
            yield f"data: {json.dumps(average_values)}\n\n"
        except (TypeError, ValueError):
            yield f"data: {json.dumps({'error': 'Invalid data'})}\n\n"
        finally:
            if end_index >= num_rows:
                end_index = 0  # Loop back to the beginning of the data
            index = end_index
            start_index = index
            end_index = start_index + current_interval

            time.sleep(current_interval)

@app.route('/stream_setup', methods=['POST'])
def stream_setup():
    """
    Sets up streaming parameters (household and interval).

    Expects JSON payload with 'household' and 'interval' parameters.

    Returns:
    - json: Status message indicating success or error.
    """
    global current_household, current_interval
    data = request.get_json()
    household = data.get('household')
    interval = data.get('interval')

    if not household or not interval:
        return jsonify({'error': 'Household and interval parameters are required.'}), 400
    elif household.upper() not in ("A", "B", "C"):
        return jsonify({'error': 'Unrecognized house.'}), 400
    try:
        interval = int(interval)
    except ValueError:
        return jsonify({'error': 'Interval must be an integer.'}), 400

    if interval <= 0:
        return jsonify({'error': 'Interval must be > 0 seconds.'}), 400

    current_household = household
    current_interval = interval

    return jsonify({'status': 'Streaming setup successful'}), 200
    
@app.route('/stream_qstats', methods=['GET'])
def stream_stats():
    """
    Computes and streams statistics (median, std_dev, critical_value_0.01) for the current household.

    Returns:
    - json: JSON object containing computed statistics.
    """
    global current_household, current_interval
    clean_data = get_household_data(df=tmp, household=current_household)

    # Select data between 25th and 75th percentiles
    q25 = clean_data.quantile(0.25)
    q75 = clean_data.quantile(0.75)
    iqr_data = clean_data[(clean_data >= q25) & (clean_data <= q75)].dropna()

    if len(iqr_data) == 0:
        return jsonify({'error': 'No valid data found for statistics calculation.'}), 404

    num_rows = len(iqr_data)
    window_size = current_interval
    averages = []

    for start_index in range(0, num_rows - window_size + 1, window_size):
        end_index = start_index + window_size
        window_data = iqr_data.iloc[start_index:end_index]
        average_values = window_data.mean().round(3).to_dict()
        averages.append(average_values)

    if not averages:
        return jsonify({'error': 'No valid data found for statistics calculation.'}), 404

    average_sample = pd.DataFrame(averages).mean()

    # Calculate median, standard deviation
    median = average_sample.median()
    q25 = average_sample.quantile(0.25)
    q75 = average_sample.quantile(0.75)
    # Fit the best distribution
    best_distribution, best_params = fit_best_distribution(average_sample)

    # Calculate right-tailed critical region value at significance level of 0.01
    critical_value = best_distribution.ppf(0.99, *best_params)

    stats_data = {
        '25p':round(q25,3),
        'median': round(median,3),
        '75p':round(q75,3),
        'rt_critical_value_0.01': round(critical_value,3),
        'best_distribution': best_distribution.name
    }

    return jsonify(stats_data)

def fit_best_distribution(data):
    """
    Fits various statistical distributions to data and selects the best fit using the Kolmogorov-Smirnov test.

    Parameters:
    - data (pd.Series or pd.DataFrame): Data for which distributions are fitted.

    Returns:
    - scipy.stats.rv_continuous: Best-fit distribution.
    - tuple: Parameters of the best-fit distribution.
    """
    distributions = [stats.norm, stats.expon, stats.gamma, stats.beta, stats.weibull_min, stats.weibull_max] #we should also try: stats.gamma, stats.beta, stats.weibull_min, stats.weibull_max
    best_distribution = None
    best_p_value = np.inf

    for distribution in distributions:
        params = distribution.fit(data)
        _, p_value = stats.kstest(data, distribution.name, args=params)
        if p_value < best_p_value:
            best_distribution = distribution
            best_p_value = p_value
            best_params = params

    return best_distribution, best_params

@app.route('/stream_data', methods=['GET'])
def stream_sse():
    """
    Initiates Server-Sent Events (SSE) for streaming averaged household data.

    Returns:
    - Response: SSE response object streaming averaged data.
    """
    st_index = request.args.get('start_index', default=0, type=int)
    return Response(stream_data(index=st_index), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
