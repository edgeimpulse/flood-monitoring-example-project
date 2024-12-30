FROM node:bullseye-slim

# APT packages
RUN apt update && apt install -y python3 python3-pip portaudio19-dev libopencv-dev python3-opencv
# RUN apt update && apt install -y curl
RUN python3 -m pip install --upgrade pip==20.3.4

RUN npm install --unsafe-perm -g edge-impulse-linux@latest --force

# Set our working directory
WORKDIR /usr/src/app

# Copy requirements.txt first for better cache on later pushes
COPY requirements.txt requirements.txt

# pip install python deps from requirements.txt on the resin.io build server
RUN pip install -r requirements.txt

# This will copy all files in our root to the working  directory in the container
COPY . ./

# main.py will run when container starts up on the device
CMD ["python3","-u","src/app.py"]
