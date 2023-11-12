FROM python

WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

RUN pip install -r requirements.txt

# Make port 8000 available to the world outside this container
EXPOSE 8000

RUN pip install docker

CMD [ "python", "load_balancer.py" ]
