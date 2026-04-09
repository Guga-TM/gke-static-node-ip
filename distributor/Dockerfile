FROM python:3.12-slim

WORKDIR /app

# Copy requirements first for better caching
COPY distributor/requirements.txt ./requirements.txt

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY logger.py distributor/distributor.py ./

# Command to run the application
CMD ["python", "-u", "distributor.py"]