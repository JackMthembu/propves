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
    PATH="/home/site/wwwroot/antenv/bin:${PATH}" \
    PYTHONPATH="/home/site/wwwroot:/home/site/wwwroot/antenv/lib/python3.11/site-packages"

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
    python3-venv \
    && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends msodbcsql17 \
    && rm -rf /var/lib/apt/lists/*

# Create necessary directories and set permissions
RUN mkdir -p /home/LogFiles /home/site/wwwroot/app_logs /opt/startup \
    && chown -R 1000:1000 /home/site/wwwroot /home/LogFiles

# Set up virtual environment
RUN python -m venv /home/site/wwwroot/antenv \
    && . /home/site/wwwroot/antenv/bin/activate

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN /home/site/wwwroot/antenv/bin/pip install --no-cache-dir -r requirements.txt \
    && /home/site/wwwroot/antenv/bin/pip install gunicorn==23.0.0 pyodbc \
    && /home/site/wwwroot/antenv/bin/pip install viztracer

# Copy project files
COPY . .

# Create startup script with proper environment setup
RUN echo '#!/bin/bash\n\
mkdir -p /home/LogFiles\n\
source /home/site/wwwroot/antenv/bin/activate\n\
cd /home/site/wwwroot\n\
if [ -f app.py ]; then\n\
    APP_MODULE="app:app"\n\
elif [ -f wsgi.py ]; then\n\
    APP_MODULE="wsgi:app"\n\
else\n\
    echo "Neither app.py nor wsgi.py found!"\n\
    exit 1\n\
fi\n\
exec /home/site/wwwroot/antenv/bin/gunicorn \
--bind=0.0.0.0:8000 \
--workers=4 \
--timeout=600 \
--access-logfile=/home/LogFiles/docker.log \
--error-logfile=/home/LogFiles/docker.err \
--capture-output \
--log-level=debug \
--chdir=/home/site/wwwroot \
"$APP_MODULE"' > /opt/startup/startup.sh \
&& chmod +x /opt/startup/startup.sh

# Expose port
EXPOSE 8000

# Set startup command
CMD ["/opt/startup/startup.sh"]
