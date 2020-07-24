FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8-alpine3.10

COPY requirements.txt .

RUN apk update && apk add --no-cache --virtual .build-deps build-base python3-dev libffi-dev

# Install dependencies
RUN pip install -r requirements.txt

# Remove the development packages
RUN apk del --no-cache .build-deps

COPY . /app
WORKDIR /app

EXPOSE 8000
