FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt /app

RUN apt-get update && apt-get install -y ffmpeg python3 python3-pip
RUN mkdir -p /app/media

RUN pip install -r requirements.txt --no-cache-dir
COPY . /app
EXPOSE ${FLASK_PORT:-8000}
CMD ["python", "bot.py"]
