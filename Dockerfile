FROM python:latest
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "./run_bot.py"]