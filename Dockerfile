FROM python:3.13-slim

ARG PBS_REPO_KEY_URL=https://repo.metacentrum.cz/key.asc
ARG PBS_SSH_USER=petrb
ARG PBS_SSH_PASSWORD=replace-me
ARG PBS_KRB_CONF_HOST=skirit.ics.muni.cz
ARG PBS_CONF_HOST=tarkil.grid.cesnet.cz

ENV PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.8.3 \
    PIP_NO_CACHE_DIR=1 \
    KRB5_CONFIG=/env/krb5.conf \
    PYTHONPATH=/app/src:/app/src/providers/pbs/OpenPBS

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        curl \
        gcc \
        gnupg \
        libssl-dev \
        make \
        openssh-client \
        pkg-config \
        python3-dev \
        python3-venv \
        sshpass \
        swig \
    && curl -fsSL "$PBS_REPO_KEY_URL" -o /tmp/key.asc \
    && install -d -m 0755 /usr/share/keyrings \
    && cat /tmp/key.asc | gpg --dearmor | tee /usr/share/keyrings/metacentrum-repo.gpg > /dev/null \
    && chmod 644 /usr/share/keyrings/metacentrum-repo.gpg \
    && install -d -m 0755 /etc/apt/trusted.gpg.d \
    && cp /usr/share/keyrings/metacentrum-repo.gpg /etc/apt/trusted.gpg.d/metacentrum-repo.gpg \
    && rm /tmp/key.asc \
    && printf '%s\n' \
        "deb [signed-by=/usr/share/keyrings/metacentrum-repo.gpg] https://repo.metacentrum.cz/ all main pilot" \
        "deb [signed-by=/usr/share/keyrings/metacentrum-repo.gpg] https://repo.metacentrum.cz/ bookworm main pilot" \
        "deb-src [signed-by=/usr/share/keyrings/metacentrum-repo.gpg] https://repo.metacentrum.cz/ all main pilot" \
        "deb-src [signed-by=/usr/share/keyrings/metacentrum-repo.gpg] https://repo.metacentrum.cz/ bookworm main pilot" \
        > /etc/apt/sources.list.d/metacentrum.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        krb5-user \
        libopenpbs-dev \
        postgresql-common \
    && yes | /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh \
    && apt-get install -y --no-install-recommends postgresql-client-18 \
    && sshpass -p "$PBS_SSH_PASSWORD" scp \
        -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null \
        "$PBS_SSH_USER@$PBS_KRB_CONF_HOST:/etc/krb5.conf" /etc/krb5.conf \
    && sshpass -p "$PBS_SSH_PASSWORD" scp \
        -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null \
        "$PBS_SSH_USER@$PBS_CONF_HOST:/etc/pbs.conf" /etc/pbs.conf \
    && pip install --no-cache-dir "poetry==$POETRY_VERSION" \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml poetry.lock* /app/
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-interaction --no-ansi

COPY src /app/src

RUN cd /app/src/providers/pbs/OpenPBS && make

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]