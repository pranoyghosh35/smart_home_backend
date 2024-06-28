"""
This module creates a fake dataset with n_days of data at 1-second resolution for three households (A, B, C).
Household A is assumed to be the home of a day worker, Household B is an office, and Household C is the home 
of someone doing shift work. The dataset includes energy consumption (in kW-min) measured by three sub-meters 
(AC, Geyser, Overall). The energy consumption patterns are generated based on realistic usage scenarios.

Assumptions:
- Household A (Day Worker): AC is used during evening/night hours, Geyser is used in the morning and evening, 
  and there is always some baseline overall energy consumption.
- Household B (Office): AC is used during office hours (9 AM - 5 PM), Geyser is rarely used, and there is 
  higher overall energy consumption during office hours.
- Household C (Shift Worker): AC and Geyser usage varies depending on the shift (night/day), and there is 
  always some baseline overall energy consumption which varies with the shift.
"""

import pandas as pd
import numpy as np

# User input for number of days
n_days = int(input("How many days to generate? "))
num_seconds = n_days * 24 * 60 * 60  # Number of seconds in n_days

# User input for introducing errors
introduce_errors = input("Do you want to introduce errors? (Y/N): ").strip().upper()
if introduce_errors == 'Y':
    error_interval = int(input("Introduce errors after how many seconds? "))
else:
    error_interval = None

households = ['A', 'B', 'C']
meters = ['AC', 'Geyser', 'Overall']

def ac_usage_pattern(household, hour):
    """
    Generate realistic AC usage patterns based on household type and time of day.

    Args:
        household (str): The household identifier (A, B, or C).
        hour (int): The current hour of the day.

    Returns:
        float: The energy consumption for AC in kW-min.
    """
    if household == 'A':  # Day Worker
        return 1.5 if 18 <= hour < 23 or 0 <= hour < 7 else 0  # Evening/Night
    elif household == 'B':  # Office
        return 2.0 if 9 <= hour < 17 else 0  # Office Hours
    elif household == 'C':  # Shift Worker
        return 1.5 if 22 <= hour < 24 or 0 <= hour < 6 else 1.5 if 10 <= hour < 14 else 0  # Night/Day
    return 0

def geyser_usage_pattern(household, hour):
    """
    Generate realistic Geyser usage patterns based on household type and time of day.

    Args:
        household (str): The household identifier (A, B, or C).
        hour (int): The current hour of the day.

    Returns:
        float: The energy consumption for Geyser in kW-min.
    """
    if household == 'A':  # Day Worker
        return 3.0 if 6 <= hour < 8 or 18 <= hour < 20 else 0  # Morning/Evening
    elif household == 'B':  # Office
        return 0  # Rarely used
    elif household == 'C':  # Shift Worker
        return 3.0 if 5 <= hour < 7 or 21 <= hour < 23 else 0  # Before/After Shift
    return 0

def overall_usage_pattern(household, hour, ac, geyser):
    """
    Generate realistic overall energy consumption patterns based on household type, 
    time of day, and individual appliance usage.

    Args:
        household (str): The household identifier (A, B, or C).
        hour (int): The current hour of the day.
        ac (float): The energy consumption for AC in kW-min.
        geyser (float): The energy consumption for Geyser in kW-min.

    Returns:
        float: The overall energy consumption in kW-min.
    """
    # Always some baseline usage
    baseline = 0.5
    # Add some random other appliance usage
    other_usage = np.random.uniform(0.1, 1.0)
    # Total is the sum of baseline, AC, Geyser, and other random appliances
    return baseline + ac + geyser + other_usage

def introduce_random_error(value):
    """
    Introduce random errors into the data.

    Args:
        value (float): The original value.

    Returns:
        float: The value with a random error introduced.
    """
    error_type = np.random.choice(['negative', 'large', 'missing'])
    if error_type == 'negative':
        return -np.abs(value)  # Negative value
    elif error_type == 'large':
        return value * np.random.uniform(10, 100)  # Unusually large value
    elif error_type == 'missing':
        return np.nan  # Missing value
    return value

# Create a dictionary to hold data for each column
data = {f"{household}_{meter}": [] for household in households for meter in meters}

# Populate the data dictionary
for second in range(num_seconds):
    hour = (second // 3600) % 24
    for household in households:
        ac = ac_usage_pattern(household, hour)
        geyser = geyser_usage_pattern(household, hour)
        overall = overall_usage_pattern(household, hour, ac, geyser)
        
        if introduce_errors == 'Y' and second % error_interval == 0:
            ac = introduce_random_error(ac)
            geyser = introduce_random_error(geyser)
            overall = introduce_random_error(overall)
        
        data[f"{household}_AC"].append(ac)
        data[f"{household}_Geyser"].append(geyser)
        data[f"{household}_Overall"].append(overall)

# Convert the dictionary to a DataFrame
df = pd.DataFrame(data)

# Save to CSV with appropriate file name
f_path="server_data_homes/"
if introduce_errors == 'Y':
    fname='realistic_fake_energy_data_with_errors.csv'
else:
    fname='realistic_fake_energy_data_without_errors.csv'
df.to_csv(str(f_path+fname))
print("Dataset generated and saved as ",str(f_path+fname))
