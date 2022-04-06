FROM python:3.8-slim-buster

WORKDIR /

COPY requirements.txt requirements.txt


COPY const.py const.py
COPY protocol.py protocol.py
COPY slave.py slave.py 

EXPOSE 8000/tcp
EXPOSE 5000/udp


CMD [ "python3", "slave.py"]
