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
    SCM_DO_BUILD_DURING_DEPLOYMENT=1 \
    ACCEPT_EULA=Y \
    PATH="/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
    PYTHONPATH="/home/site/wwwroot" \
    FLASK_APP="/home/site/wwwroot/app.py"

# Set work directory
WORKDIR /home/site/wwwroot

# Install system dependencies including ODBC driver
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    default-libmysqlclient-dev \
    pkg-config \
    openssh-server \
    curl \
    sqlite3 \
    gnupg2 \
    unixodbc \
    unixodbc-dev \
    && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends msodbcsql17 \
    && rm -rf /var/lib/apt/lists/*

# Create necessary directories and set permissions
RUN mkdir -p /home/LogFiles /home/site/wwwroot/app_logs /opt/startup \
    && chown -R 1000:1000 /home/site/wwwroot /home/LogFiles

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install gunicorn==23.0.0 pyodbc \
    && pip install viztracer

# Copy project files
COPY . .

# Create both startup scripts (for Azure and local)
RUN echo '#!/bin/bash\n\
mkdir -p /home/LogFiles\n\
cd /home/site/wwwroot\n\
\n\
# Debug information\n\
echo "Current directory: $(pwd)"\n\
echo "Python path: $PYTHONPATH"\n\
echo "Files in current directory:"\n\
ls -la\n\
\n\
# Start gunicorn\n\
exec gunicorn \
--bind=0.0.0.0:8000 \
--workers=4 \
--timeout=600 \
--access-logfile=/home/LogFiles/docker.log \
--error-logfile=/home/LogFiles/docker.err \
--capture-output \
--log-level=debug \
--chdir=/home/site/wwwroot \
app:app' > /opt/startup/startup.sh \
&& chmod +x /opt/startup/startup.sh \
&& cp /opt/startup/startup.sh /home/site/wwwroot/startup.sh \
&& chmod +x /home/site/wwwroot/startup.sh

# Create a simple Flask app if it doesn't exist
RUN if [ ! -f app.py ]; then \
    echo 'from flask import Flask\n\
app = Flask(__name__)\n\
\n\
@app.route("/")\n\
def hello():\n\
    return "Hello from Azure App Service!"' > app.py; \
fi

# Expose port
EXPOSE 8000

# Set startup command to use Azure's expected path
CMD ["/home/site/wwwroot/startup.sh"]
