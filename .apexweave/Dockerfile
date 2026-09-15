ARG APEXWEAVE_STACK=python:3.12
FROM registry.apexweaveapp.com:5000/apexweave-stack-${APEXWEAVE_STACK}
COPY . .
RUN --mount=type=cache,target=/root/.cache/pip sh /opt/apexweave/build.sh
EXPOSE 8000
HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=3 CMD curl -sf -o /dev/null http://localhost:8000/ || exit 1
CMD ["sh", "/opt/apexweave/start.sh"]
