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

    parser.add_argument("--infile", "-f", help="Enter sqs ID ")
    parser.add_argument("--queue", "-q", help="Enter path to folder containing zipfiles")                    

    #queue_url = "https://sqs.eu-central-1.amazonaws.com/080708105962/crunchbase-dev-mvos-lambda-cdx-queue"
    args = parser.parse_args()

    # Retrieve list of companies from csv file 
    df_comp = pd.read_csv(args.infile,header=None)
    comp_nested = df_comp.values
    companies = [c[0] for c in comp_nested]

    # Convert companies list into multiple message bodies;
    # Send corresponding messages to SQS queue
    for i,comp in enumerate(chunk_join(companies,5)):
        res = send_custom_message(args.queue,comp,i)
        print(f"Message ID: {res['MessageId']}")

if __name__ == "__main__":
    main()