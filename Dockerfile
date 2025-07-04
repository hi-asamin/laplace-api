FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry lock && \
    poetry install --only main --no-interaction --no-ansi
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
