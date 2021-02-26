import boto3
import os
import requests
import csv
from urllib.parse import urlparse
from urllib.error import URLError


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

def sqs_send_message(content):
    # Create SQS client
    sqs = boto3.client('sqs')

    queue_url = os.environ['sqs_fetch_id']

    response = sqs.send_message(
        QueueUrl=queue_url,
        DelaySeconds=10,
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
        MessageBody=(
            f'My message:{content}')
    ) 
    return response

def restore_domain(domain,url):
    """Restore original domain name in CDX url"""
    domain_split = domain.split('.')
    domain_split.reverse()
    domain_key = ",".join(domain_split) + ')'
    
    new = url.replace(domain_key,domain)
    
    return new

def chunks(L, n):
    """ Yield successive n-sized chunks from L """
    for i in range(0, len(L), n):
        yield L[i:i+n]

def sqs_send_urls(domain,records):
    """Format cdx response and send in batches to sqs"""

    # Restore original domain in CDX url
    rec_list = [[restore_domain(domain,url),time,dgst] for url,time,dgst in records]   
    
    # Filter out urls with non-text extension
    blacklist = ['.css','.js','.map','.xml','.png','.woff','.gif','.jpg',
                '.JPG','.jpeg','.bmp','.mp4','.svg','woff2','.ico','.ttf']
    rec_filtered = [[url,time,dgst] for url,time,dgst in rec_list if not url.endswith(tuple(blacklist))] 

    # Divide list into batches of 5 records; send batch to sqs
    for rec in chunks(rec_filtered,5):
        response = sqs_send_message(rec)
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