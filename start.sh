#!/bin/bash

# Start the Streamlit app in the background
streamlit run st_app.py --server.port=8501 --server.address=0.0.0.0 &

# Start the Flask app
python app.py
