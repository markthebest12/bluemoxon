FROM mcr.microsoft.com/playwright/python:v1.40.0-focal

WORKDIR /app

# Install AWS Lambda Runtime Interface Client
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt awslambdaric

# Copy handler
COPY handler.py .

# Install Chromium browser
RUN playwright install chromium

# Make files readable by Lambda's sandbox user (runs as different UID at runtime)
# Lambda overrides USER directive, so we need world-readable files
RUN chmod -R 755 /app && chmod 644 /app/*.py /app/*.txt

# Switch to non-root user for security scanning compliance
# Note: Lambda overrides this at runtime with its own sandbox user
USER pwuser

# Set the entrypoint for Lambda
ENTRYPOINT [ "python", "-m", "awslambdaric" ]
CMD [ "handler.handler" ]
