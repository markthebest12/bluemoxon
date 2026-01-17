FROM public.ecr.aws/lambda/python:3.12-arm64

# Accept VERSION as build argument (default to dev for local builds)
ARG VERSION=0.0.0-dev

# Copy backend models (single source of truth)
COPY backend/app/__init__.py /opt/python/app/
COPY backend/app/models/ /opt/python/app/models/

# Make models readable by Lambda's sandbox user
RUN chmod -R 755 /opt/python

# Bake VERSION into image for tracking
RUN echo "$VERSION" > /opt/python/VERSION

ENV PYTHONPATH=/opt/python:$PYTHONPATH

# Install dependencies
COPY backend/lambdas/image_processor/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download rembg models
COPY backend/lambdas/image_processor/download_models.py .
RUN python download_models.py
RUN rm download_models.py

# Copy handler
COPY backend/lambdas/image_processor/handler.py ${LAMBDA_TASK_ROOT}/

# Switch to non-root user for security scanning compliance
# Note: Lambda overrides this at runtime with its own sandbox user
USER 1000

CMD ["handler.lambda_handler"]
