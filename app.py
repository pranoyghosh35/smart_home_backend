from flask import Flask, request, Response, jsonify, redirect
import subprocess
import pandas as pd
import numpy as np
import time
import json
from scipy import stats

app = Flask(__name__)

start_index = 0  # Global variable for start_index

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

def stream_data():
    """
    Generator function to stream averaged household data.

    Yields:
    - str: JSON-formatted string containing average values of AC, Geyser, Overall.
    """
    global start_index
    household_data = get_household_data(data, current_household)
    num_rows = len(household_data)
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
            
@app.route('/', methods=['GET'])
def run_st_app():
    return redirect("http://0.0.0.0:8501")

@app.route('/stream_setup', methods=['POST'])
def stream_setup():
    """
    Sets up streaming parameters (household, interval, and optionally start_index).

    Expects JSON payload with 'household' and 'interval' parameters.
    Optionally accepts 'start_index'.

    Returns:
    - json: Status message indicating success or error.
    """
    global current_household, current_interval, start_index
    data = request.get_json()
    household = data.get('household')
    interval = data.get('interval')
    start_idx = data.get('start_index', 0)  # Default to 0 if not provided

    if not household or not interval:
        return jsonify({'error': 'Household and interval parameters are required.'}), 400
    elif household.upper() not in ("A", "B", "C"):
        return jsonify({'error': 'Unrecognized house.'}), 400
    try:
        interval = int(interval)
        start_idx = int(start_idx)
    except ValueError:
        return jsonify({'error': 'Interval and start_index must be integers.'}), 400

    if interval <= 0:
        return jsonify({'error': 'Interval must be > 0 seconds.'}), 400

    current_household = household
    current_interval = interval
    start_index = start_idx  # Update global start_index

    return jsonify({'status': 'Streaming setup successful'}), 200

def fit_best_distribution(data):
    """
    Fits various statistical distributions to data and selects the best fit using the Kolmogorov-Smirnov test.

    Parameters:
    - data (pd.Series or pd.DataFrame): Data for which distributions are fitted.

    Returns:
    - scipy.stats.rv_continuous: Best-fit distribution.
    - tuple: Parameters of the best-fit distribution.
    """
    distributions = [stats.norm, stats.expon]  # Add more distributions as needed
    best_distribution = None
    best_p_value = np.inf
    best_params = ()  # Initialize best_params as an empty tuple

    for distribution in distributions:
        params = distribution.fit(data)
        _, p_value = stats.kstest(data, distribution.name, args=params)
        if p_value < best_p_value:
            best_distribution = distribution
            best_p_value = p_value
            best_params = params

    return best_distribution, best_params
    
@app.route('/stream_qstats', methods=['GET'])
def stream_stats():
    """
    Computes and streams statistics (median, std_dev, critical_value_0.01) for the current household.

    Returns:
    - json: JSON object containing computed statistics or an error message.
    """
    clean_data = get_household_data(df=tmp, household=current_household)

    # Select data between 25th and 75th percentiles
    q25 = clean_data.quantile(0.25)
    median = clean_data.median()
    q75 = clean_data.quantile(0.75)
    iqr_data = clean_data[(clean_data >= q25) & (clean_data <= q75)].dropna()

    if len(iqr_data) == 0:
        return jsonify({'error': 'No valid data found for statistics calculation.'}), 404

    # Calculate the number of complete intervals in the data
    num_intervals = len(iqr_data) // current_interval

    # Initialize lists to store average values
    avg_values_list = []

    # Iterate over each interval
    for i in range(num_intervals):
        # Calculate start and end indices for each interval
        start_idx = i * current_interval
        end_idx = start_idx + current_interval
        
        # Slice the interval data
        interval_data = iqr_data.iloc[start_idx:end_idx]
        
        # Calculate average for each column
        avg_values = interval_data.mean()
        
        # Append the averages to avg_values_list
        avg_values_list.append(avg_values)

    # Create a DataFrame from avg_values_list
    average_sample = pd.DataFrame(avg_values_list, columns=['AC', 'Geyser', 'Overall'])
    
    # Calculate statistics
    median_val = median.round(3).to_dict()
    q25_val = q25.round(3).to_dict()
    q75_val = q75.round(3).to_dict()
    
    # Initialize dictionaries to store results
    critical_values = {}
    best_distributions = {}

    # Fit distributions and calculate critical values for each column separately
    for column_name in average_sample.columns:
        column_data = average_sample[column_name]
        
        try:
            best_distribution, best_params = fit_best_distribution(column_data)
            
            # Store the best distribution name for the column
            best_distributions[column_name] = best_distribution.name if best_distribution is not None else None
            
            # Calculate right-tailed critical region value at significance level of 0.01
            if best_distribution is not None:
                critical_value = best_distribution.ppf(0.99, *best_params)
                critical_values[column_name] = round(critical_value, 3)
            else:
                critical_values[column_name] = None
        
        except Exception as e:
            # Handle exceptions by logging or returning an error response
            return jsonify({'error': f"Error calculating statistics for {column_name}: {str(e)}"}), 404
          
    stats_data = {
        '25p': q25_val,
        'median': median_val,
        '75p': q75_val,
        'rt_critical_value_0.01': critical_values,
        'best_distribution': best_distributions
    }    
    
    return jsonify(stats_data)

@app.route('/stream_data', methods=['GET'])
def stream_sse():
    """
    Initiates Server-Sent Events (SSE) for streaming averaged household data.

    Returns:
    - Response: SSE response object streaming averaged data.
    """
    return Response(stream_data(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
