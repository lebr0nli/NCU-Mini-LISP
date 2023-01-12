FROM python:3.9-slim-buster

RUN pip install -U lark rich

WORKDIR /app
COPY mlisp.py /app/
COPY mlisp.lark /app/

CMD ["python", "mlisp.py"]
