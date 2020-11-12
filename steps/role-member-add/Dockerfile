FROM relaysh/core:latest-python
RUN pip install --upgrade google-api-python-client google-auth google-auth-httplib2 oauth2client
COPY "./step.py" "/entrypoint.py"
ENTRYPOINT []
CMD ["python3", "/entrypoint.py"]

LABEL "org.opencontainers.image.title"="Update GCP IAM Policy"
LABEL "org.opencontainers.image.description"="This step updates the IAM policy specifying roles and members in GCP"
LABEL "com.puppet.nebula.sdk.version"="v1"
