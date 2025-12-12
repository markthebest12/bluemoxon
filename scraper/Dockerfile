FROM mcr.microsoft.com/playwright/python:v1.40.0-focal

WORKDIR /app

# Install AWS Lambda Runtime Interface Client
COPY --chown=pwuser:pwuser requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt awslambdaric

# Copy handler with proper ownership for non-root user
COPY --chown=pwuser:pwuser handler.py .

# Install Chromium browser
RUN playwright install chromium

# Ensure app directory is accessible by pwuser
RUN chown -R pwuser:pwuser /app

# Switch to non-root user for security
USER pwuser

# Set the entrypoint for Lambda
ENTRYPOINT [ "python", "-m", "awslambdaric" ]
CMD [ "handler.handler" ]
