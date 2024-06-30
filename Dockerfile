# Use the official Python image as a base image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any dependencies needed by the Flask app
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port that Flask is running on
EXPOSE 5000

# Make port 8501 available to the world outside this container (for Streamlit)
EXPOSE 8501

# Copy and run the shell script to start both Flask and Streamlit apps
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Command to run the start script
CMD ["/start.sh"]
