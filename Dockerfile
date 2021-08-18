FROM python:3.9.6
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "./run_bot.py"]