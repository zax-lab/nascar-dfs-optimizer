# Use apache/airflow:2.8.0-python3.11 as base image
FROM apache/airflow:2.8.0-python3.11

# Set AIRFLOW_HOME
ENV AIRFLOW_HOME=/opt/airflow
ENV AIRFLOW__CORE__DAGS_FOLDER=/opt/airflow/dags
ENV AIRFLOW__CORE__PLUGINS_FOLDER=/opt/airflow/plugins

# Set working directory
WORKDIR $AIRFLOW_HOME

# Copy requirements.txt
COPY requirements.txt .

# Install custom Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy DAGs
COPY dags/ $AIRFLOW_HOME/dags/

# Create necessary directories
RUN mkdir -p $AIRFLOW_HOME/dags $AIRFLOW_HOME/plugins $AIRFLOW_HOME/logs

# Expose Airflow webserver port
EXPOSE 8080

# Default command (can be overridden in docker-compose)
CMD ["airflow", "standalone"]
