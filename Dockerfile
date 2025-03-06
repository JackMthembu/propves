# Use official Python runtime as base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=8000 \
    WEBSITE_SITE_NAME=propves \
    WEBSITE_HOSTNAME=propves.azurewebsites.net \
    WEBSITE_ROLE_INSTANCE_ID=0 \
    WEBSITE_INSTANCE_ID=f19f17d318573e91b9f48a927b55cc10f33adb9462bf0cb4602e0d53a47e62e1 \
    SCM_DO_BUILD_DURING_DEPLOYMENT=1

# Set work directory
WORKDIR /home/site/wwwroot

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    default-libmysqlclient-dev \
    pkg-config \
    openssh-server \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Create necessary directories and set permissions
RUN mkdir -p /home/LogFiles /home/site/wwwroot/app_logs /opt/startup \
    && chown -R 1000:1000 /home/site/wwwroot /home/LogFiles

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install gunicorn==23.0.0 \
    && pip install viztracer  # For code profiling

# Copy project files
COPY . .

# Create startup script
RUN echo '#!/bin/bash\n\
mkdir -p /home/LogFiles\n\
exec gunicorn --bind 0.0.0.0:8000 \
--workers 4 \
--timeout 600 \
--access-logfile /home/LogFiles/docker.log \
--error-logfile /home/LogFiles/docker.err \
--capture-output \
--log-level info \
app:app' > /opt/startup/startup.sh \
&& chmod +x /opt/startup/startup.sh

# Expose port
EXPOSE 8000

# Set startup command
CMD ["/opt/startup/startup.sh"]
