FROM python

WORKDIR /app
    
COPY server.py .
    
COPY requirements.txt /app/
    
RUN pip install -r requirements.txt

#debug
RUN pip install docker
    
CMD ["python", "server.py"]
    