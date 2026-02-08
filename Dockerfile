FROM python:3
ENV PYTHONUNBUFFERED 1
COPY . /django-gentelella/
WORKDIR /django-gentelella
RUN pip install -r requirements.txt
WORKDIR /django-gentelella/gentelella
