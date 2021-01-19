import boto3

# Create SQS client
sqs = boto3.client('sqs')

def main():
    queue_url = "https://sqs.eu-central-1.amazonaws.com/080708105962/terraform-example-queue-rjbood"

    # Send message to SQS queue
    response = sqs.send_message(
        QueueUrl=queue_url,
        DelaySeconds=10,
        MessageAttributes={
            'Title': {
                'DataType': 'String',
                'StringValue': 'First message'
            },
            'Author': {
                'DataType': 'String',
                'StringValue': 'rjbood'
            },
        },
        MessageBody=(
            "2ie-edu.org,"
            "aaaid.org,"
            "aacb.org"
        )
    )

    print(response['MessageId'])

if __name__ == "__main__":
    main()