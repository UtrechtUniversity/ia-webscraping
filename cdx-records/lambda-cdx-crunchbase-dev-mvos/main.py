import boto3
import os
import requests
import pandas as pd


def handler(event, context):
    print("Started lambda-sqs example.")
    sqs_receive_messages()

def sqs_receive_messages():
    # Create SQS client
    sqs = boto3.client('sqs')

    queue_url = os.environ['sqs_id']

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
    print('Received and Deleted message: %s' % message)

def handle_message(message):
    urls = message['Body'].split(',')
    for url in urls:
        get_urls(url)

def get_urls(domain):
        payload = {
            'url': domain,
            'matchType': 'prefix',
            'fl': 'urlkey,timestamp,statuscode',
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
            return

        header = response_list[0]
        if not response_list[-2]:
            resume_key = response_list[-1][0]
            urls = response_list[1:-2]  # The before last one is always empty -> -2
        else:
            resume_key = "finished"
            urls = response_list[1:]

        #print(f"The domain {domain} has {len(urls)} urls/snapshots")
        
        df_urls = pd.DataFrame(urls,index=None)
        csv_file = f"/tmp/cdx_records_{domain}.csv"
        df_urls.to_csv(csv_file,header=False,index=False)

        s3_resource = boto3.resource(service_name ='s3',region_name = 'EU (Frankfurt) eu-central-1')

        bucket_name = "crunchbase-dev-mvos-source"
        s3_resource.meta.client.upload_file(
            Filename=csv_file,Bucket=bucket_name,Key=f'pilot100_v2/{csv_file}')