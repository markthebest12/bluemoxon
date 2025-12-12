FROM mcr.microsoft.com/playwright/python:v1.40.0-focal

WORKDIR /app

# Install AWS Lambda Runtime Interface Client
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt awslambdaric

# Copy handler
COPY handler.py .

# Install Chromium browser
RUN playwright install chromium

# Set the entrypoint for Lambda
ENTRYPOINT [ "python", "-m", "awslambdaric" ]
CMD [ "handler.handler" ]
