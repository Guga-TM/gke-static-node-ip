FROM python:3.12-slim

WORKDIR /app

# Copy requirements first for better caching
COPY fixer/requirements.txt ./requirements.txt

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY logger.py fixer/functions.py fixer/fixer.py fixer/server.py ./

ENV PYTHONUNBUFFERED="1"

# Command to run the application
CMD ["gunicorn", \
    "-w", "1", \
    "-b", "0.0.0.0:6924", \
    "--log-level", "error", \
    "--capture-output", \
    "--error-logfile",  "-", \
    "server:app"]