import boto3

# Create SQS client
sqs = boto3.client('sqs')

def main():
    queue_url = "https://sqs.eu-central-1.amazonaws.com/080708105962/crunchbase-dev-mvos-lambda-cdx-queue"

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
                'StringValue': 'mvos'
            },
        },
        MessageBody=(
            "bitpanda.com,"
            "musictraveler.com,"
            "ikangai.com,"
            "medicus.ai,"
            "refurbed.de,"
            "usound.com,"
            "bikemap.net,"
            "bsurance.tech,"
            "checkyeti.com,"
            "parkbob.com,"
            "getbyrd.com,"
            "nuki.io,"
            "blockpit.io,"
            "morpher.com,"
            "imagebiopsylab.ai,"
            "getmimo.com"
        )
    )

    print(response['MessageId'])

if __name__ == "__main__":
    main()