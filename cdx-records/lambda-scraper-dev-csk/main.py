import asyncio
import json
import os
import re
import requests
import tempfile
import time

import boto3

from aiohttp import ClientSession
from bs4 import BeautifulSoup


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


async def fetch(record, session):
    data = json.loads(record['body'])
    url = data['url']
    file_name = data['file_name']
    bucket_name = data['bucket_name']

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
                # get text
                strings = list(body.strings)
                # get text
                text = clean_text(strings)

                if text != '':
                    s3 = boto3.resource('s3')
                    s3.Object(bucket_name, file_name).put(Body=text)

            except Exception as e:
                print(e)
            

async def fetch_all(records):
    tasks = []
    fetch.start_time = dict() 
    async with ClientSession() as session:
        for record in records:
            task = asyncio.ensure_future(fetch(record, session))
            tasks.append(task) 
        _ = await asyncio.gather(*tasks) 


def lambda_handler(event, context):
    # wrapper results

    print('-->', len(event['Records']))

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

    print(workload)

    #lambda_handler(workload, None)



    # # iterate over the records in this message/event
    # for record in event['Records']:
    #     # get the necessary data: url, filename and bucket
    #     data = json.loads(record['body'])
    #     url = data['url']
    #     file_name = data['file_name']
    #     bucket_name = data['bucket_name']

        # s3 client
        # s3_client = boto3.client('s3')
        
    #     # start fetching
    #     try:
    #         # request
    #         resp = requests.get(url)
    #         if resp.status_code == 200:
    #             # resp.content is a byte array, convert to string
    #             response = resp.content.decode("utf-8", "ignore")
    #             # strip style, script, svg
    #             response = clean_html(response)
    #             # parse
    #             soup = BeautifulSoup(response, 'html.parser')
    #             # locate the body
    #             body = soup.body
    #             # get text
    #             strings = list(body.strings)
    #             # get text
    #             text = clean_text(strings)

    #             # store
    #             if text != '':
    #                 s3 = boto3.resource('s3')
    #                 s3.Object(bucket_name, file_name).put(Body=text)
            
    #             # append to result
    #             result_body.append( { 'url': url, 'statusCode': 200 })

    #         else:
    #             result_body.append( { 'url': url, 'statusCode': resp.status_code })

    #     except Exception as e:
    #         result_body.append({ 'url': url, 'statusCode': 400, 'message': str(e) })

    # return {
    #     'statusCode': 200,
    #     'body': json.dumps(result_body)
    # }
