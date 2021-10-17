FROM python:slim

RUN pip install --upgrade pip

WORKDIR /app
COPY . /app

RUN pip3 install -r requirements.txt

CMD [ "python3", "main.py"]