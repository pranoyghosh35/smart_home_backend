import streamlit as st
import requests
import base64
from datetime import datetime

web_prefix="https://smart-home-backend-95to.onrender.com"
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
    response = requests.post(str(web_prefix+'/stream_setup'), json=data)
    return response.json()

# Function to open the website in a new tab using JavaScript
def open_website_in_tab(url):
    js = f"window.open('{url}')"  # JavaScript to open a new tab
    html = f"<script>{js}</script>"
    st.markdown(html, unsafe_allow_html=True)
    
# Function to load an image and convert it to a base64 string
def get_image_as_base64(image_path):
    with open(image_path, 'rb') as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# Display title with an icon and help button
col1, col2, col3 = st.columns([1, 8, 1])
with col1:
    st.image('server_data_homes/images/st_icon.png', width=100)  # Adjust width as needed
with col2:
    st.title('Welcome to the Smart Energy Meter')
with col3:
    help_url = "https://pranoyghosh35.github.io/smart_home_backend/"
    help_icon_path = "server_data_homes/images/help.png"  # Path to your local help icon
    help_icon_base64 = get_image_as_base64(help_icon_path)
    help_icon_html = f'<a href="{help_url}" target="_blank"><img src="data:image/png;base64,{help_icon_base64}" width="30"/></a>'
    st.markdown(help_icon_html, unsafe_allow_html=True)

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
    st.write("Request sent. Please wait...")
    response = setup_streaming(household, interval)

    if response.get('status')=="Streaming setup and stats calculation successful":
        st.success(response.get('status'))
        st.write('Streaming is set up successfully. You can now access the data and statistics websites below.')

        # Display hyperlinks to open data and stats websites
        st.markdown(f"[Open Stats Website]({web_prefix}/stream_qstats)")
        st.markdown(f"[Open Data Website]({web_prefix}/stream_data)")

    else:
        st.error(response.get('error'))
