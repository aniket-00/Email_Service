# Use a lightweight Python base image
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install Flask and other dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Flask application code to the container
COPY . .

# Expose the Flask app port
EXPOSE 5000

# Define the command to run the Flask app
CMD ["python", "app.py"]
