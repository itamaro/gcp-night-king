FROM python:3.6

# Install Python dependencies using Pipenv with system-level flags
# ("ignore-pipfile" so only the lock file is used)
COPY Pipfile Pipfile.lock /app/
RUN cd /app \
    && pip install --no-cache-dir --upgrade pip pipenv \
    && pipenv install --ignore-pipfile --deploy --system

# Bring in the app itself
ADD nightking /app/nightking
WORKDIR /app/nightking
ENTRYPOINT ["python", "lurker.py"]
