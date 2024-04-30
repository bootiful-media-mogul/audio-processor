#!/usr/bin/env python3
import json
import os
import typing
import uuid
from concurrent.futures import ThreadPoolExecutor

import pika
import boto3
from flask import Flask
import podcast
import rmq
import utils

DEBUG = os.environ.get('DEBUG', 'false') == 'true'

def download(s3, s3p: str, output_file: str) -> str:
    def s3_download(s3, bucket_name: str, key: str, local_fn: str):
        s3.meta.client.download_file(bucket_name, key, local_fn)
        assert os.path.exists(local_fn), f"the local file {local_fn} should have been downloaded"
        return local_fn

    import typing
    parts: typing.List[str] = s3p.split("/")
    bucket, folder, fn = parts[2:]
    local_fn: str = output_file
    the_directory: str = os.path.dirname(local_fn)
    if not os.path.exists(the_directory):
        os.makedirs(the_directory)
    assert os.path.exists(the_directory), f"the directory {the_directory} should exist but does not."
    utils.log("going to download %s to %s" % (s3p, local_fn))
    try:
        utils.log(f'going to download {bucket}/{folder}/{fn}')
        s3_download(s3, bucket, os.path.join(folder, fn), local_fn)
        assert os.path.exists(local_fn), (
                "the file should be downloaded to %s, but was not." % local_fn
        )
    except BaseException as e:
        utils.log('something has gone horribly awry when trying to download the S3 file: %s' % e)

    return local_fn


def s3_uri(bucket_name: str, upload_key: str) -> str:
    return f's3://{bucket_name}/{upload_key}'


def handle_podcast_episode_creation_request(s3,
                                            properties: pika.BasicProperties,
                                            incoming_json_request: typing.Any,
                                            uid: str):
    utils.log(f'incoming request: {incoming_json_request}')
    output_s3_uri = incoming_json_request['outputS3Uri']
    segments = incoming_json_request['segments']
    segments = [a['s3Uri'] for a in segments]
    tmp_dir = os.path.join(os.environ['HOME'], 'podcast-production', uid)
    os.makedirs(tmp_dir, exist_ok=True)
    local_files = [download(s3, s3_uri, os.path.join(tmp_dir, s3_uri.split('/')[-1])) for s3_uri in segments]
    local_files_segments = [podcast.Segment(lf, os.path.splitext(lf)[1][1:], crossfade_time=100) for lf in local_files]
    output_podcast_audio_local_fn = podcast.create_podcast(local_files_segments, os.path.join(tmp_dir, 'output.mp3'),
                                                           output_extension='mp3')
    utils.log(f'the produced audio is stored locally {output_podcast_audio_local_fn}')

    s3_parts = output_s3_uri[len('s3://'):]
    utils.log(s3_parts)
    bucket, folder, file = s3_parts.split('/')
    s3.meta.client.upload_file(output_podcast_audio_local_fn, bucket, f'{folder}/{file}')
    return {'outputS3Uri': output_s3_uri}

def build_s3_client() -> typing.Any:
    aws_region = os.environ["AWS_REGION"]
    aws_key_id = os.environ['AWS_ACCESS_KEY_ID']
    aws_key_secret = os.environ['AWS_ACCESS_KEY_SECRET']

    def good_string(s: str) -> bool:
        if s is not None and isinstance(s, str):
            if s.strip() != '':
                return True
        return False

    for k, v in {'access-key-secret': aws_key_secret,
                 'access-key-id': aws_key_id,
                 'access-region': aws_region}.items():
        assert good_string(v), f'the value for {k} is invalid'

    boto3.setup_default_session(
        aws_secret_access_key=aws_key_secret,
        aws_access_key_id=aws_key_id,
        region_name=aws_region)

    s3 = boto3.resource("s3")
    return s3


if __name__ == "__main__":

    def run_flask():
        app = Flask(__name__)

        @app.route("/")
        def hello():
            return json.dumps({"status": "HODOR"})

        utils.log("about to start the Flask service")
        # on my local machine it'll run on 7070, so as to not conflict with the API
        # but in prod it'll run on 7080
        port = int(os.environ.get('SERVER_PORT', '7070'))
        utils.log(f"launching Flask thread on port {port}.")
        app.run(port=port)


    def run_rmq():
        retry_count = 0
        max_retries = 5
        while retry_count < max_retries:
            try:
                retry_count += 1
                utils.log("launching RabbitMQ background thread")
                requests_q = 'podcast-processor-requests'

                def build_rmq_uri():
                    rmq_username = os.environ['RMQ_USERNAME']
                    rmq_pw = os.environ['RMQ_PASSWORD']
                    rmq_host = os.environ['RMQ_HOST']
                    rmq_vhost = os.environ['RMQ_VIRTUAL_HOST']
                    rmq_address = f'rmq://{rmq_username}:{rmq_pw}@{rmq_host}/{rmq_vhost}'
                    if DEBUG:
                        for k, v in os.environ.items():
                            utils.log(f'\t{k} = {v}')
                        utils.log(f'RMQ address: {rmq_address}')
                    return rmq_address

                rmq_uri = utils.parse_uri(build_rmq_uri())
                s3 = build_s3_client()

                def handler(properties, json_request) -> str:
                    return handle_podcast_episode_creation_request(
                        s3, properties, json_request, str(uuid.uuid4()))

                try:
                    rmq.start_rabbitmq_processor(
                        requests_q,
                        rmq_uri["host"],
                        rmq_uri["username"],
                        rmq_uri["password"],
                        rmq_uri["path"],
                        handler,
                    )
                except Exception as ex:
                    utils.exception(
                        ex,
                        message="There was some sort of error "
                                "installing a RabbitMQ listener."
                                "Restarting the processor... ",
                    )
            except Exception as e:
                utils.exception(
                    e,
                    message="something went wrong trying to "
                            "start the RabbitMQ processing thread!",
                )

        utils.log("Exhausted retry count of %s times." % max_retries)


    with ThreadPoolExecutor() as executor:
        for f in [run_flask, run_rmq]:
            executor.submit(f)
