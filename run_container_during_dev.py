#!/usr/bin/env python3
import os
import subprocess

"""
run this in the dev shell with all the environment variables from .envrc loaded
"""

container_id = subprocess.run(["docker", "build", "."], capture_output=True, text=True)
container_id = container_id.stderr.split(os.linesep)
container_id = [l for l in container_id if "writing image" in l][0]
container_id = container_id.split(":")[1].split(" ")[0]
host = "host.docker.internal"
envs = """
AWS_ACCESS_KEY_ID
AWS_ACCESS_KEY_SECRET
AWS_REGION
BW_SESSION
DB_HOST
DB_PASSWORD
DB_SCHEMA
DB_USERNAME
IDP_ISSUER_URI
OPENAI_KEY
PODBEAN_CLIENT_ID
PODBEAN_CLIENT_SECRET
PODCASTS_PROCESSOR_RMQ_REPLIES
PODCASTS_PROCESSOR_RMQ_REQUESTS
PODCAST_ASSETS_S3_BUCKET
PODCAST_ASSETS_S3_BUCKET_FOLDER
PODCAST_INPUT_S3_BUCKET
PODCAST_OUTPUT_S3_BUCKET
RMQ_ADDRESS
RMQ_HOST
RMQ_PASSWORD
RMQ_USERNAME
RMQ_VIRTUAL_HOST
SPRING_DATASOURCE_PASSWORD
SPRING_DATASOURCE_URL
SPRING_DATASOURCE_USERNAME
SPRING_RABBITMQ_PASSWORD
SPRING_RABBITMQ_USERNAME
SPRING_RABBITMQ_VIRTUAL_HOST
""".split(
    os.linesep
)
envs = [a.strip() for a in envs if a.strip() != ""]
envs = [(a, os.getenv(a)) for a in envs]
envs = [(a, e.replace("localhost", host).replace("127.0.0.1", host)) for (a, e) in envs]
envs = ["-e %s=%s" % (a, '"%s"' % e) for (a, e) in envs]
cmd = "docker run %s %s" % (" ".join(envs), container_id)
print(cmd)

