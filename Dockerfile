FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY configs ./configs
COPY deploy ./deploy

RUN pip install --no-cache-dir --upgrade pip &&     pip install --no-cache-dir .

ENTRYPOINT ["holdings-monitor"]
CMD ["run"]
