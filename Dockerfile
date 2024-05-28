# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file to the working directory
COPY requirements.txt /app/

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code to the working directory
COPY . /app

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Define environment variable to point to the app location
ENV FLASK_APP=api/app.py

# Run the application
CMD ["flask", "run", "--host=0.0.0.0"]
