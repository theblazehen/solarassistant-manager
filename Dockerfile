FROM ubuntu:22.04
RUN apt-get update && apt-get install -y python3 python3-pip && pip3 install paho-mqtt
COPY . /app
CMD ["python3", "/app/main.py"]
