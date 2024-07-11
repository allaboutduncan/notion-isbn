# syntax = docker/dockerfile:experimental

# Comments are provided throughout this file to help you get started.
# If you need more help, visit the Dockerfile reference guide at
# https://docs.docker.com/go/dockerfile-reference/

ARG PYTHON_VERSION=3.12.1
FROM python:${PYTHON_VERSION}-slim as base

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Download dependencies as a separate step to take advantage of Docker's caching.
# Leverage a cache mount to /root/.cache/pip to speed up subsequent builds.
# Leverage a bind mount to requirements.txt to avoid having to copy them into
# into this layer.
# RUN python -m pip install -r requirements.txt

# Switch to the non-privileged user to run the application.
RUN apt-get update && apt-get install -y git
RUN pip3 install --upgrade pip --user
RUN pip3 install --upgrade awscli
RUN pip3 install git+https://github.com/Wyattjoh/pushover
RUN pip3 install ndg-httpsclient pyopenssl pyasn1 urllib3
RUN pip3 install requests datetime schedule boto3 pillow beautifulsoup4 --user
# Copy the source code into the container.
COPY . .

# Expose the port that the application listens on.
EXPOSE 3331

# Run the application.
CMD python3 main.py
