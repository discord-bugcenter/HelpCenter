FROM python:3.9.6
WORKDIR /app
ENV PYTHONUNBUFFERED=0
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "./main.py"]
