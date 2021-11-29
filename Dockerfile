FROM python:3.9

WORKDIR /project

ARG PIP_NO_CACHE_DIR=0
COPY requirements-dev.txt requirements-dev.txt
RUN pip install --requirement requirements-dev.txt

COPY setup.py setup.py
COPY ac_calc ac_calc

ARG SETUP_COMMAND=develop
RUN python setup.py $SETUP_COMMAND
