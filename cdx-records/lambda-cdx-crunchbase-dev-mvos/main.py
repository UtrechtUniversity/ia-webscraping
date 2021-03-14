import boto3
import csv
import json
import os
import re
import requests

from urllib.parse import urlparse
from urllib.error import URLError

EXTENSIONS = [
    '.css','.js','.map','.xml','.png','.woff','.gif','.jpg', 'eot',
    '.jpeg','.bmp','.mp4','.svg','woff2','.ico','.ttf', 'robots.txt'
]

BLACKLIST = [
    re.compile(ext + '(\?|$)', re.IGNORECASE) for ext in EXTENSIONS
]

BATCH_SIZE = 25


def handler(event, context):
    print("Started lambda-sqs example.")
    sqs_receive_messages()

def sqs_receive_messages():
    # Create SQS client
    sqs = boto3.client('sqs')

    queue_url = os.environ['sqs_cdx_id']

    # Receive message from SQS queue
    response = sqs.receive_message(
        QueueUrl=queue_url,
        AttributeNames=[
            'SentTimestamp'
        ],
        MaxNumberOfMessages=1,
        MessageAttributeNames=[
            'All'
        ],
        VisibilityTimeout=0,
        WaitTimeSeconds=0
    )

    if 'Messages' in response:
        message = response['Messages'][0]
        receipt_handle = message['ReceiptHandle']

        handle_message(message)

        # Delete received message from queue
        sqs.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=receipt_handle
        )
    else:
        message = 'None'
    print(f'Received and Deleted message: {message}')

def handle_message(message):
    urls = message['Body'].split(',')
    for url in urls:
        domain = get_domain(url)
        records = get_urls(domain)
        if records:
            sqs_send_urls(domain,records)

def get_domain(url):
    try:
        domain = urlparse(url).netloc
        domain = domain.replace("www.", "")
        return domain
    except URLError as e: 
        print(f"Not a valid url:{e}")
        pass        

def get_urls(domain):
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
        filtered_urls = set()

        # Get response from url
        response = requests.get('http://web.archive.org/cdx/search/cdx', params=payload)
        response_list = response.json()

        # Extraction
        if not response_list:
            print(f"No records available: {domain}")
            return None

        header = response_list[0]
        if not response_list[-2]:
            resume_key = response_list[-1][0]
            urls = response_list[1:-2]  # The before last one is always empty -> -2
        else:
            resume_key = "finished"
            urls = response_list[1:]

        return urls

def sqs_send_message(content, delay_offset=0):
    # Create SQS client
    sqs = boto3.client('sqs')

    queue_url = os.environ['sqs_fetch_id']
    target_bucket = os.environ['target_bucket_id']

    [url, timestamp] = content
    file_name = (f'{url}.{timestamp}.txt').replace('/', '_')

    body = {
        'url': f'http://web.archive.org/web/{timestamp}/{url}',
        'file_name': file_name,
        'bucket_name': target_bucket
    }
    response = sqs.send_message(
        QueueUrl=queue_url,
        DelaySeconds=10 + delay_offset,
        MessageAttributes={
                'Title': {
                    'DataType': 'String',
                    'StringValue': f'Message nr '
                },
                'Author': {
                    'DataType': 'String',
                    'StringValue': 'mvos'
                },
            },
        MessageBody=json.dumps(body)
    ) 
    return response

def restore_domain(domain,url):
    """Restore original domain name in CDX url"""
    domain_split = domain.split('.')
    domain_split.reverse()
    domain_key = ",".join(domain_split) + ')'
    
    new = url.replace(domain_key,domain).strip()
    
    return new

def chunks(L, n):
    """ Yield successive n-sized chunks from L """
    for i in range(0, len(L), n):
        yield L[i:i+n]

def sqs_send_urls(domain,records):
    """Format cdx response and send in batches to sqs"""

    # Restore original domain in CDX url
    rec_list = [[restore_domain(domain,url),time,dgst] for url,time,dgst in records]   
    
    # filter out unwanted urls and identical pages
    rec_filtered = {}
    for [url, time, dgst] in rec_list:
        if dgst not in rec_filtered.keys() and \
            not any([bool(r.search(url)) for r in BLACKLIST]):

            rec_filtered[dgst] = [url, time]

    # note the provided delay seconds, first 25 (BATCH_SIZE) have 
    # a delaytime of 10, the next batch has a delay time of 20
    for i, (_, rec) in enumerate(rec_filtered.items()):
        response = sqs_send_message(rec, 10 + 10 *( i // BATCH_SIZE))
        print(f"Sent message {response['MessageId']} to fetch queue")

def main():
    """Test script to run from command line"""

    message = (
            "https://moonvision.io/,"
            "http://www.enpulsion.com/,"
            "https://kiweno.com,"
            "https://rateboard.io,"
            "https://www.meetfox.com,"
            "https://etudo.co/?lang=en,"
            "http://www.finnest.at,"
            "http://www.journiapp.com,"
            "https://www.prime-crowd.com/,"
            "https://www.intellyo.com"
    )
        
    urls = message.split(',')
    for url in urls:
        domain = get_domain(url)
        records = get_urls(domain)
        if records:
            print(f"Records found for {domain}; sending to sqs")
            sqs_send_urls(domain,records)

if __name__ == "__main__":
    main()