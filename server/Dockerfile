FROM python:3.12

WORKDIR /app
    
COPY fibonacci.py .
    
COPY requirements.txt /app/
    
RUN pip install -r requirements.txt
    
CMD ["python", "fibonacci.py"]
    