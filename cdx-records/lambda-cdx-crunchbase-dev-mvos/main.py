import boto3
import csv
import json
import os
import re
import requests
import aiohttp
import asyncio
import time
import logging
import sys

from urllib.parse import urlparse
from urllib.error import URLError

if os.environ.get('logging'):
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
else:
    logging.basicConfig(stream=sys.stdout, level=logging.ERROR)
logger = logging.getLogger()

EXTENSIONS = [
    '.css','.js','.map','.xml','.png','.woff','.gif','.jpg', 'eot',
    '.jpeg','.bmp','.mp4','.svg','woff2','.ico','.ttf', 'robots.txt'
]

BLACKLIST = [
    re.compile(ext + '(\?|$)', re.IGNORECASE) for ext in EXTENSIONS
]

TARGET_BUCKET = os.environ.get('target_bucket_id')

# Define queues as SQS resource
FETCH_SQS_LIMIT = 2000
sqs = boto3.resource('sqs')
fetch_sqs_queue = sqs.Queue(os.environ['sqs_fetch_id'])
cdx_sqs_queue = sqs.Queue(os.environ['sqs_cdx_id'])

def fetch_queue_limit_reached():
    return int(fetch_sqs_queue.attributes.get('ApproximateNumberOfMessages')) > FETCH_SQS_LIMIT

def get_cdx_sqs_messages():
    response = cdx_sqs_queue.receive_messages(
        AttributeNames=[
            'SentTimestamp'
        ],
        MaxNumberOfMessages=10,
        MessageAttributeNames=[
            'All'
        ],
        VisibilityTimeout=3,
        WaitTimeSeconds=10
    )

    logger.info("Received '%d' sqs messages from cdx queue", len(response))
    return response

def get_domain(url):
    try:
        domain = urlparse(url).netloc
        domain = domain.replace("www.", "")
        return domain
    except URLError as e: 
        logger.error("Not a valid url: %s", e)
        pass        

async def get_urls_async(messages):
    tasks=[]
    async with aiohttp.ClientSession() as session:
        for message in messages:
            url = message.body
            domain = get_domain(url)
            task = asyncio.ensure_future(get_urls(message.message_id, message.receipt_handle, domain, session))
            tasks.append(task)
        task_results = await asyncio.gather(*tasks)
    return task_results

async def get_urls(sqs_message_id, sqs_receipt_handle, domain, session):
    payload = {
            'url': domain,
            'matchType': 'prefix',
            'fl': 'urlkey,timestamp,digest',
            'collapse': 'timestamp:4',
            'from': '2018',
            'to': '2019',
            'filter':'mimetype:text/html',
            'filter':'statuscode:200',
            # 'showDupeCount': 'true',
            # 'showSkipCount': 'true',
            # 'limit': '4',
            'output': 'json',
            'showResumeKey': 'true',
        }

    async with session.get('http://web.archive.org/cdx/search/cdx', params=payload) as response:
        response_list = await response.json()

    # Extraction
    if not response_list:
        logger.info("No records available for '%s'", domain)
        return {
            "domain" : domain,
            "urls" : None
        }

    header = response_list[0]
    if not response_list[-2]:
        resume_key = response_list[-1][0]
        urls = response_list[1:-2]  # The before last one is always empty -> -2
    else:
        resume_key = "finished"
        urls = response_list[1:]

    return {
        "sqs_message_id" : sqs_message_id,
        "sqs_receipt_handle" : sqs_receipt_handle,
        "domain" : domain,
        "urls" : urls
    }

def restore_domain(domain,url):
    """Restore original domain name in CDX url"""
    domain_split = domain.split('.')
    domain_split.reverse()
    domain_key = ",".join(domain_split) + ')'
    
    new = url.replace(domain_key,domain).strip()
    
    return new

def filter_urls(domain, records):
    # Restore original domain in CDX url
    rec_list = [[restore_domain(domain,url),time,dgst] for url,time,dgst in records]   
    
    ## filter out unwanted urls and identical pages
    rec_filtered = {}
    for [url, time, dgst] in rec_list:
        if dgst not in rec_filtered.keys() and \
            not any([bool(r.search(url)) for r in BLACKLIST]):

            rec_filtered[dgst] = [url, time]
    return rec_filtered

def send_urls_to_fetch_sqs_queue(urls):
    delay_offset=0
    messages_send=0
    id = 0 # every message in a batch must have a unique ID
    batch_messages = []
    for i, (_, rec) in enumerate(urls.items()):
        [url, timestamp] = rec
        file_name = (f'{url}.{timestamp}.txt').replace('/', '_')
              
        if len(batch_messages) == 10:
            sqs_send_message_batch(batch_messages)
            messages_send += 10
            if ((delay_offset < 900) and (messages_send % 30 == 0)):
                # for every 30 messages send; increase message delay with 10 seconds
                delay_offset += 10
            batch_messages = []
            
        id += 1
        batch_messages.append(
            { 
                'Id': str(id),
                'MessageBody': json.dumps({
                    'url': f'http://web.archive.org/web/{timestamp}/{url}',
                    'file_name': file_name,
                    'bucket_name': target_bucket
                }),
                'DelaySeconds': delay_offset,
                'MessageAttributes': {
                    'Title': {
                        'DataType': 'String',
                        'StringValue': f'Message nr '
                    },
                    'Author': {
                        'DataType': 'String',
                        'StringValue': 'mvos'
                    },
                }
            }
        )
    #Send last messages
    print(f"messages send: {messages_send + len(batch_messages)}")
    if len(batch_messages) > 0:
        sqs_send_message_batch(batch_messages)
        batch_messages = []
   

def sqs_send_message_batch(messages):
    response = fetch_sqs_queue.send_messages(
        Entries=messages
    )
    if response.get('Failed'):
        logger.warning("Failed to send the following messages to SQS: '%s'", str(response['Failed']))
    else:
        pass
        #logger.info("Successfully send the following messages to SQS: '%s'", str(response['Successful']))

def chunks(L, n):
    """ Yield successive n-sized chunks from L """
    for i in range(0, len(L), n):
        yield L[i:i+n]

def handler(event, context):
    logger.info("Started CDX Lambda")

    ## Check number of messages in Fetch queue
    if fetch_queue_limit_reached():
        logger.info("Number of messages in fetch sqs queue higher than limit of '%d'; early return", FETCH_SQS_LIMIT)
        return

    ## get messages from CDX Queue
    messages = get_cdx_sqs_messages()

    ## get Urls from internet archive (async)
    task_results = asyncio.run(get_urls_async(messages))

    ## Filter urls, send filtered urls to sqs
    processed_messages = []
    print(len(task_results))
    for result in task_results:
        if result['urls'] is None:
            # No URLS found, continue with next one TODO: should we delete this message?
            continue
        print("number of urls found: " + str(len(result['urls'])))

        ## Send filtered urls to fetch SQS queue
        send_urls_to_fetch_sqs_queue(filter_urls(result['domain'], result['urls']))
        processed_messages.append({
            'Id': result['sqs_message_id'],
            'ReceiptHandle': result['sqs_receipt_handle']
        })

    ## Delete processed SQS messages CDX queue in batches of 10
    for proc_messages_batch in chunks(processed_messages, 10):
        print("delete the following messages from cdx queue: " + str(proc_messages_batch))
        cdx_sqs_queue.delete_messages(
            Entries=proc_messages_batch
        )

def main():
    """Test script to run from command line"""

    message = (
        "http://www.usound.com/,"
        "https://www.bikemap.net,"
        "https://www.bsurance.tech,"
        "https://www.checkyeti.com,"
        "http://parkbob.com,"
        "https://playerhunter.com/,"
        "https://www.derbrutkasten.com,"
        "https://www.oktav.com,"
        "http://www.healcloud.com,"
        "https://www.involve.me"
    )
        
    urls = message.split(',')
    total_n_records = 0
    message_id = 0
    batch_messages = []
    for url in urls:
        #send messages to sqs
        message_id += 1
        batch_messages.append(
            { 
                'Id': str(message_id),
                'MessageBody': url,
                'DelaySeconds': 0
            }
        )
    cdx_sqs_queue.send_messages(
        Entries=batch_messages
    )
    
    handler(None, None)



if __name__ == "__main__":
    tic = time.perf_counter()
    
    main()

    toc = time.perf_counter()
    print(f"Program runtime {toc - tic:0.4f} seconds")
    