FROM debian:bullseye-slim

RUN apt-get update && apt-get install -y python3 python3-pip \
    gcc libffi-dev libxml2-dev libxslt1-dev build-essential \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .
CMD ["python3", "bot.py"]
