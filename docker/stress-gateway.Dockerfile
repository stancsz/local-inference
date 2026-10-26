FROM local-inference-gateway:latest
COPY local-inference/tmp/stress/sift-candidate/src /opt/sift/src
RUN pip install --no-cache-dir --no-deps /opt/sift
COPY local-inference/app /app
COPY local-inference/gateway.yaml /app/gateway.yaml
