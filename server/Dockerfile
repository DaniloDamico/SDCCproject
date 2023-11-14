FROM python

WORKDIR /app
    
COPY server.py .
    
COPY requirements.txt /app/
    
RUN pip install -r requirements.txt
    
CMD ["python", "server.py"]
    