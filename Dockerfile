# Use an official Python runtime as a parent image.
FROM python:3.10-slim

# Set the working directory in the container.
WORKDIR /flask-app

# Copy requirements.txt and install dependencies.
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Expose port 5000.
EXPOSE 5000

# Copy the entrypoint script and make it executable.
COPY entrypoint.sh /flask-app/entrypoint.sh
RUN chmod +x /flask-app/entrypoint.sh

# Set the entrypoint.
ENTRYPOINT ["/bin/bash", "/flask-app/entrypoint.sh"]
