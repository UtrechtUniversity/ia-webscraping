import argparse
import boto3
import pandas as pd
from pathlib import Path

def chunk_join(lst,n):
    """Yield successive n-sized chunks from lst;
       join elements in single string per chunk"""
    for i in range(0, len(lst), n):
        try:
            elements = lst[i:i + n]
            yield ','.join(elements)
        except:
            pass

def send_custom_message(queue_url,content,index=1):
    """send message with custom content and attributes to sqs queue"""
    
    # Create SQS client
    sqs = boto3.client('sqs')
    
    response = sqs.send_message(
            QueueUrl=queue_url,
            DelaySeconds=10,
            MessageAttributes={
                'Title': {
                    'DataType': 'String',
                    'StringValue': f'Message nr {index}'
                },
                'Author': {
                    'DataType': 'String',
                    'StringValue': 'mvos'
                },
            },
            MessageBody=(content)
            )
    return response

def main():
    parser = argparse.ArgumentParser(description='Fill sqs queue with urls for which CDX records should be fetched')
    parser.add_argument("--queue", "-q", help="Enter sqs ID ")
    parser.add_argument("--infile", "-f", help="Enter path to folder containing zipfiles")    
    args = parser.parse_args()

    boto3.setup_default_session(profile_name='crunch')             
    #queue_url = "https://sqs.eu-central-1.amazonaws.com/080708105962/crunchbase-dev-mvos-lambda-cdx-queue"
    queue_url = args.queue 

    # Retrieve list of companies from csv file 
    df_comp = pd.read_csv(args.infile)
    companies = list(df_comp['Website'])

    # Convert companies list into single message bodies;
    # Send corresponding messages to SQS queue
    for i,comp in enumerate(companies):
        res = send_custom_message(queue_url,comp,i)

        print(f"Message ID: {res['MessageId']}")
        print(f"Message : {res}")

if __name__ == "__main__":
    main()