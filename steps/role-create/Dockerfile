FROM relaysh/core:latest-python
RUN pip install --upgrade google-api-python-client oauth2client
COPY "./step.py" "/entrypoint.py"
ENTRYPOINT []
CMD ["python3", "/entrypoint.py"]

LABEL "org.opencontainers.image.title"="Create GCP IAM Roles"
LABEL "org.opencontainers.image.description"="This step creates custom IAM roles in GCP"
LABEL "com.puppet.nebula.sdk.version"="v1"
