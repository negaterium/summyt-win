# 1. Use an official Python runtime as a parent image
FROM python:3.11-slim

# 2. Set the working directory in the container
WORKDIR /app

# 3. Copy the requirements file and install dependencies
COPY requirements.txt .
# Install PyTorch CPU-only version first, then the rest
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# 4. Copy the application source code into the container
COPY src/ /app/src/

# 5. Copy the assets directory
COPY assets/ /app/assets/

# 6. Expose the port the app runs on
EXPOSE 5000

# 7. Define the command to run the application
CMD ["python", "src/server.py"]

