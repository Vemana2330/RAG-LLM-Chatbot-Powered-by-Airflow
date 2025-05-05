FROM apache/airflow:2.10.4-python3.11

COPY requirements.txt .

# Force pip to use prebuilt wheels and avoid source builds
ENV PIP_NO_BUILD_ISOLATION=1
ENV PIP_ONLY_BINARY=:all:

RUN pip install --no-cache-dir -r requirements.txt

USER airflow
