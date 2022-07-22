FROM python:3.10.5
WORKDIR /app
ENV PYTHONUNBUFFERED=0
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY ./src .
CMD ["python", "./main.py"]
