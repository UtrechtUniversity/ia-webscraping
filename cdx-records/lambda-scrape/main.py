import asyncio
import json
import logging
import os
import re
import requests
import tempfile
import time

import boto3

from aiohttp import ClientSession
from bs4 import BeautifulSoup

# create a global sqs client
SQS_CLIENT = boto3.client('sqs')

# logging
logger = logging.getLogger()
if os.environ.get('scraper_logging_level', 'error') == "info":
    logger.setLevel(logging.INFO)
else:
    logger.setLevel(logging.ERROR)

# failure sqs
failure_sqs_queue = os.environ.get('sqs_failures_id','https://sqs.eu-central-1.amazonaws.com/080708105962/terraform-example-queue-rjbood')


def clean_html(response):
    """strips svg / script / style tags"""
    # remove svg
    response = re.sub(r'<svg[\s\S]+?/svg>', '', response)
    # remove script
    response = re.sub(r'<script[\s\S]+?/script>', '', response)
    # remove style
    response = re.sub(r'<style[\s\S]+?/style>', '', response)
    # return
    return response


def clean_text(text):
    """cleans a string list from beautifulsoup, 
    removes excess whitespace"""
    # strip every item
    text = [item.strip() for item in text]
    # and loose all blank items
    text = [item for item in text if item != '']
    # create one string and return
    return '\n'.join(text)


def send_fail_message(queue, url, reason='unknown'):
    body = {
        'url': url,
        'reason': reason
    }
    SQS_CLIENT.send_message(
        QueueUrl=queue,
        DelaySeconds=1,
        MessageAttributes={
            'Author': {
                'DataType': 'String',
                'StringValue': 'scraper lambda'
            },
        },
        MessageBody=json.dumps(body)
    ) 
    return True


async def fetch(record, session):
    data = json.loads(record['body'])
    url = data['url']
    file_name = data['file_name']
    bucket_name = data['bucket_name']

    # failure queue
    failure_queue = failure_sqs_queue

    async with session.get(url) as response:
        r = await response.read()
        if response.status == 200:
            try:
                # resp.content is a byte array, convert to string
                contents = r.decode("utf-8", "ignore")
                # strip style, script, svg
                contents = clean_html(contents)
                # parse
                soup = BeautifulSoup(contents, 'html.parser')
                # locate the body
                body = soup.body

                if body is not None:
                    # get text
                    strings = list(body.strings)
                    # get text
                    text = clean_text(strings)

                    if text != '':
                        s3 = boto3.resource('s3')
                        s3.Object(bucket_name, file_name).put(Body=text)

                else:
                    logger.info(f'scraper lambda could not find any text: "{url}"')
                    send_fail_message(failure_queue, url, 'no html text found in body')

            except Exception as e:
                logger.error(f'scraper lambda failed to scrape "{url}"\nException: {str(e)}')
                send_fail_message(failure_queue, url, str(e))

        else:
            logger.error(f'scraper lambda failed to scrape "{url}"\nResponse status: {response.status}')
            send_fail_message(
                failure_queue, 
                url, 
                f'response status: {response.status}'
            )

            

async def fetch_all(records):
    tasks = []
    fetch.start_time = dict() 
    async with ClientSession() as session:
        for record in records:
            task = asyncio.ensure_future(fetch(record, session))
            tasks.append(task) 
        _ = await asyncio.gather(*tasks) 


def lambda_handler(event, context):
    logger.info(f'scraper lambda received {len(event["Records"])} messages')
    loop = asyncio.get_event_loop() 
    future = asyncio.ensure_future(fetch_all(event['Records'])) 
    loop.run_until_complete(future) 



if __name__ == '__main__':
    r1 = { 
        'url': 'https://hexdocs.pm/phoenix_live_view/bindings.html#click-events', 
        'file_name': 'file1.txt', 
        'bucket_name': 'whatever' 
    }

    r2 = { 
        'url': 'https://hexdocs.pm/elixir/Enum.html#reduce/2', 
        'file_name': 'file2.txt', 
        'bucket_name': 'whatever' 
    }

    workload = {
        'Records': [
            { 'body': json.dumps(r1) },
            { 'body': json.dumps(r2) }
        ]
    }

    lambda_handler(workload, None)