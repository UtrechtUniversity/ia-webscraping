import boto3

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
    # TODO: replace by input from file
    companies = [
        "bitpanda.com",
        "musictraveler.com",
        "ikangai.com",
        "medicus.ai",
        "refurbed.de",
        "usound.com",
        "bikemap.net",
        "bsurance.tech",
        "checkyeti.com",
        "parkbob.com"
        ]
    queue_url = "https://sqs.eu-central-1.amazonaws.com/080708105962/crunchbase-dev-mvos-lambda-cdx-queue"

    # Convert companies list into multiple message bodies;
    # send corresponding messages to SQS queue
    for i,cc in enumerate(chunk_join(companies,5)):
        res = send_custom_message(queue_url,cc,i)
        print(res['MessageId'])

if __name__ == "__main__":
    main()