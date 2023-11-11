FROM python

WORKDIR /app
    
COPY fibonacci.py .
    
COPY requirements.txt /app/
    
RUN pip install -r requirements.txt
    
CMD ["python", "fibonacci.py"]
    