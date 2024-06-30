import streamlit as st
import requests
from datetime import datetime

# Function to calculate the start index
def calculate_start_index():
    now = datetime.now()
    return now.hour * 3600 + now.minute * 60 + now.second

# Function to send JSON to the server and setup streaming
def setup_streaming(household, interval):
    start_index = calculate_start_index()
    data = {
        "household": household,
        "interval": interval,
        "start_index": start_index
    }
    response = requests.post('https://smart-home-backend-95to.onrender.com/stream_setup', json=data)
    return response.json()

# Function to open the website in a new tab using JavaScript
def open_website_in_tab(url):
    js = f"window.open('{url}')"  # JavaScript to open a new tab
    html = f"<script>{js}</script>"
    st.markdown(html, unsafe_allow_html=True)

# Display title with an icon and help button
col1, col2, col3 = st.columns([1, 8, 1])
with col1:
    st.image('server_data_homes/images/st_icon.png', width=100)  # Adjust width as needed
with col2:
    st.title('Welcome to the Smart Energy Meter')
with col3:
    help_url = "https://pranoyghosh35.github.io/smart_home_backend/"
    st.markdown(f'<a href="{help_url}" target="_blank"><img src="https://img.icons8.com/ios-glyphs/30/000000/help.png"/></a>', unsafe_allow_html=True)

# Step 1: Collect user input for household
household_option = st.selectbox('Select House:', ['A', 'B', 'C', 'Other'])

if household_option == 'Other':
    household = st.text_input('Enter House (single character):').upper()
else:
    household = household_option

# Step 2: Collect user input for interval
interval_option = st.selectbox('Select Interval in seconds:', [5, 15, 30, 60, 'Other'])

if interval_option == 'Other':
    interval = st.number_input('Enter interval in seconds (must be > 0):', min_value=1)
else:
    interval = interval_option

# Submit button and handling response
if st.button('Submit'):
    response = setup_streaming(household, interval)

    if response.get('status') == 'Streaming setup successful':
        st.success(response.get('status'))
        st.write('Streaming is set up successfully. You can now access the data and statistics websites below.')

        # Display hyperlinks to open data and stats websites
        st.markdown(f"[Open Stats Website](https://smart-home-backend-95to.onrender.com/stream_qstats)")
        st.markdown(f"[Open Data Website](https://smart-home-backend-95to.onrender.com/stream_data)")

    else:
        st.error(response.get('error'))
