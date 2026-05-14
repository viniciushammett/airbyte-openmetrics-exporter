# syntax=docker/dockerfile:1.7
FROM python:3.12-slim AS builder

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN python -m venv "$VIRTUAL_ENV"
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /tmp/requirements.txt \
    && python -m pip uninstall -y pip setuptools wheel

FROM python:3.12-slim AS runtime

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN groupadd --system --gid 1001 exporter \
    && useradd --system --uid 1001 --gid 1001 --home-dir /app --shell /usr/sbin/nologin exporter

WORKDIR /app
COPY --from=builder --chown=exporter:exporter /opt/venv /opt/venv
COPY --chown=exporter:exporter app/ /app/app/

USER 1001:1001
EXPOSE 8000

CMD ["python", "-m", "app.main"]
