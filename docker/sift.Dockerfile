FROM python:3.12-slim
COPY sift /opt/sift
RUN pip install --no-cache-dir /opt/sift
COPY local-inference/app /app
WORKDIR /app
CMD ["python", "proxy.py"]
