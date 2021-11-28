FROM python:3.10

WORKDIR /project

ARG PIP_NO_CACHE_DIR=0
COPY requirements.txt requirements.txt
RUN pip install --requirement requirements.txt

COPY setup.py setup.py
COPY ac_calc ac_calc

ARG SETUP_COMMAND=develop
RUN python setup.py $SETUP_COMMAND
