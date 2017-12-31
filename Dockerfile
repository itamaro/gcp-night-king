FROM python:3.6

# Install Python dependencies
COPY requirements.txt /app/
RUN cd /app && pip install --no-cache-dir -r requirements.txt

# Bring in the app itself
ADD nightking /app/nightking
WORKDIR /app/nightking
ENTRYPOINT ["python", "lurker.py"]
