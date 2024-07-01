from flask import Flask, request, Response, jsonify,render_template_string
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

# Global variables to store household, interval, and stats_data
current_household = None
current_interval = None
global_stats_data = None  # Initialize global stats_data

streamlit_process = None

@app.route('/')
def index():
    global streamlit_process
    # Check if Streamlit is already running
    if streamlit_process is None or streamlit_process.poll() is not None:
        # Start the Streamlit app
        streamlit_process = subprocess.Popen(
            ["streamlit", "run", "st_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
        )
        # Wait a bit to ensure Streamlit starts properly
        time.sleep(5)

    # Embed the Streamlit app in an iframe
    streamlit_url = 'http://127.0.0.1:8501'
    iframe_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Smart Energy Meter</title>
    </head>
    <body>
        <iframe src="{streamlit_url}" width="100%" height="1000px" frameborder="0"></iframe>
    </body>
    </html>
    """
    return render_template_string(iframe_html)

@app.route('/stop_streamlit')
def stop_streamlit():
    global streamlit_process
    if streamlit_process is not None:
        streamlit_process.terminate()
        streamlit_process = None
    return "Streamlit app stopped."

def get_household_data(df, household):
    """
    Extracts data for a specific household from the dataframe.

    Args:
        df (pd.DataFrame): The dataframe containing the data.
        household (str): The household identifier ('A', 'B', 'C').

    Returns:
        pd.DataFrame: The household data with columns renamed to 'AC', 'Geyser', 'Overall'.
    """
    household_data = df[[f"{household}_AC", f"{household}_Geyser", f"{household}_Overall"]]
    household_data.columns = ['AC', 'Geyser', 'Overall']
    return household_data

def calc_stats():
    """
    Calculates statistical data for the current household and interval.
    """
    global global_stats_data

    clean_data = get_household_data(df=tmp, household=current_household)

    q25 = clean_data.quantile(0.25)
    median = clean_data.median()
    q75 = clean_data.quantile(0.75)
    iqr_data = clean_data[(clean_data >= q25) & (clean_data <= q75)].dropna()

    if len(iqr_data) == 0:
        global_stats_data = {'error': 'No valid data found for statistics calculation.'}
        return

    num_intervals = len(iqr_data) // current_interval

    avg_values_list = []

    for i in range(num_intervals):
        start_idx = i * current_interval
        end_idx = start_idx + current_interval
        interval_data = iqr_data.iloc[start_idx:end_idx]
        avg_values = interval_data.mean()
        avg_values_list.append(avg_values)

    average_sample = pd.DataFrame(avg_values_list, columns=['AC', 'Geyser', 'Overall'])

    median_val = median.round(3).to_dict()
    q25_val = q25.round(3).to_dict()
    q75_val = q75.round(3).to_dict()

    critical_values = {}
    best_distributions = {}

    for column_name in average_sample.columns:
        column_data = average_sample[column_name]
        try:
            best_distribution, best_params = fit_best_distribution(column_data)
            best_distributions[column_name] = best_distribution.name if best_distribution is not None else None
            if best_distribution is not None:
                critical_value = best_distribution.ppf(0.99, *best_params)
                critical_values[column_name] = round(critical_value, 3)
            else:
                critical_values[column_name] = None
        except Exception as e:
            global_stats_data = {'error': f"Error calculating statistics for {column_name}: {str(e)}"}
            pass

    global_stats_data = {
        '25p': q25_val,
        'median': median_val,
        '75p': q75_val,
        'rt_critical_value_0.01': critical_values,
        'best_distribution': best_distributions
    }

@app.route('/stream_setup', methods=['POST'])
def stream_setup():
    """
    Sets up the streaming configuration.

    Expects a JSON payload with 'household', 'interval', and optional 'start_index'.

    Returns:
        JSON response indicating success or error.
    """
    global current_household, current_interval, start_index, global_stats_data
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
    global_stats_data = None  # Reset stats data

    calc_stats()  # Calculate stats immediately after setting up

    return jsonify({'status': 'Streaming setup and stats calculation successful'}), 200

def fit_best_distribution(data):
    """
    Fits the best distribution to the given data.

    Args:
        data (pd.Series): The data to fit.

    Returns:
        tuple: The best distribution and its parameters.
    """
    distributions = [stats.norm, stats.expon]  
    # Add more distributions e.g. stats.gamma, stats.beta, stats.lognorm as needed
    best_distribution = None
    best_p_value = -np.inf  # Use negative infinity to ensure proper comparison
    best_params = ()  # Initialize best_params as an empty tuple

    for distribution in distributions:
        params = distribution.fit(data)
        _, p_value = stats.kstest(data, distribution.name, args=params)
        if p_value > best_p_value:
            best_distribution = distribution
            best_p_value = p_value
            best_params = params

    return best_distribution, best_params

@app.route('/stream_qstats', methods=['GET'])
def stream_stats_route():
    """
    Returns the calculated statistical data for the current household.

    Returns:
        JSON response with the statistical data or an error message.
    """
    if global_stats_data is not None:
        return jsonify(global_stats_data)

    return jsonify({'error': 'First try stream_setup.'}), 404

def stream_data():
    """
    Streams the household data in intervals and provides status checking.

    Yields:
        str: The averaged values and their statuses in JSON format.
    """
    global start_index

    household_data = get_household_data(data, current_household)
    num_rows = len(household_data)

    def status_checking(average_values, stats_data):
        if stats_data is None:
            return "TBD"
        color = {}
        for key, value in average_values.items():
            if value < 0:
                color[key] = "Red"
            elif value < stats_data['25p'][key]:
                color[key] = "Green"
            elif value <= stats_data['75p'][key]:
                color[key] = "Yellow"
            elif value >= stats_data['rt_critical_value_0.01'][key]:
                color[key] = "Red"
            else:
                color[key] = "TBD"
        return color

    while True:
        recent_data = household_data.iloc[start_index:start_index + current_interval]
        try:
            average_values = recent_data.astype(float).mean().round(3).to_dict()
            color = status_checking(average_values, global_stats_data)
            yield f"data: {json.dumps(average_values)} status: {json.dumps(color)}\n\n"
        except (TypeError, ValueError) as e:
            yield f"data: {json.dumps({'error': 'Invalid data'})} status: 'Critical Red'\n\n"
        finally:
            start_index += current_interval
            if start_index >= num_rows:
                start_index = 0
            time.sleep(current_interval)

@app.route('/stream_data', methods=['GET'])
def stream_sse():
    """
    Endpoint for streaming household data.

    Returns:
        Response: A streaming response with household data and statuses.
    """
    return Response(stream_data(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
