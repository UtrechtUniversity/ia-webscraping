import argparse
import boto3
import pandas as pd
from pathlib import Path

def sqs_send_message_batch(messages,queue_url):
    """send batch of messages to sqs queue"""
    
    # Define queue as SQS resource
    sqs = boto3.resource('sqs')
    queue = sqs.get_queue_by_name(QueueName=queue_url)
        
    response = queue.send_messages(Entries=messages)
    
    if response.get('Failed'):
        print(f"Failed to send the following messages to SQS{str(response['Failed'])}")
    else:
        print(f"Message sent")


def send_urls_to_cdx_queue(companies,queue_url):
    """Send ten messages to cdx sqs queue, one url per message"""
    messages_send=0
    batch_messages = []

    for index,comp in enumerate(companies):

        if len(batch_messages) == 10:
            # Max batch size (N=10) reached; send batch
            sqs_send_message_batch(batch_messages,queue_url)
            batch_messages = []
            messages_send += 10

        batch_messages.append(
            { 
                'Id': str(index), # every message in a batch must have a unique ID; use index for this
                'MessageBody': (comp),
                'DelaySeconds': 10,
                'MessageAttributes': {
                    'Title': {
                        'DataType': 'String',
                        'StringValue': f'Message nr '
                    },
                    'Author': {
                        'DataType': 'String',
                        'StringValue': 'mvos'
                    }
                }
            }
        )
    #Send last messages to SQS
    if len(batch_messages) > 0 :
        sqs_send_message_batch(batch_messages,queue_url)
    

def main():
    parser = argparse.ArgumentParser(description='Fill sqs queue with urls for which CDX records should be fetched')
    parser.add_argument("--queue", "-q", help="Enter sqs ID ")
    parser.add_argument("--infile", "-f", help="Enter path to file with urls")    
    args = parser.parse_args()

    boto3.setup_default_session(profile_name='crunch')             
    #queue_url = "https://sqs.eu-central-1.amazonaws.com/080708105962/crunchbase-dev-mvos-lambda-cdx-queue"
    queue_url = args.queue 

    # Retrieve list of companies from csv file 
    df_comp = pd.read_csv(args.infile)
    companies = list(df_comp['Website'])

    # Convert companies list into single message bodies;
    # Send corresponding messages to SQS queue
    send_urls_to_cdx_queue(companies,queue_url)
    
if __name__ == "__main__":
    main()