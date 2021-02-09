import boto3
import pandas as pd

def chunk_join(lst,n):
    """Yield successive n-sized chunks from lst;
       join elements in single string per chunk"""
    for i in range(0, len(lst), n):
        elements = lst[i:i + n]
        yield ','.join(elements)

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
    queue_url = "https://sqs.eu-central-1.amazonaws.com/080708105962/crunchbase-dev-mvos-lambda-cdx-queue"

    # Retrieve list of companies from csv file 
    df_comp = pd.read_csv("companies.csv",header=None)
    comp_nested = df_comp.values
    companies = [c[0] for c in comp_nested]

    # Convert companies list into multiple message bodies;
    # Send corresponding messages to SQS queue
    for i,comp in enumerate(chunk_join(companies,5)):
        res = send_custom_message(queue_url,comp,i)
        print(res['MessageId'])

if __name__ == "__main__":
    main()