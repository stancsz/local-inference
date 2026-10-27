FROM python:3.12-slim
LABEL org.local-inference.sift-revision="2f0ef2786345fe0868b282903712fd1ac92d43fe"
COPY sift/pyproject.toml sift/README.md sift/LICENSE /opt/sift/
COPY sift/src /opt/sift/src
RUN pip install --no-cache-dir /opt/sift
RUN pip install --no-cache-dir 'litellm[proxy]==1.106.4'
COPY local-inference/app /app
COPY local-inference/gateway.yaml /app/gateway.yaml
WORKDIR /app
ENV PYTHONPATH=/app
ENV LITELLM_TELEMETRY=False
CMD ["litellm", "--config", "/app/gateway.yaml", "--host", "0.0.0.0", "--port", "8090"]
