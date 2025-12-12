FROM mcr.microsoft.com/playwright/python:v1.40.0-focal

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY handler.py .

# Install Chromium browser
RUN playwright install chromium

# Run as non-root user for security
USER pwuser

CMD ["handler.handler"]
