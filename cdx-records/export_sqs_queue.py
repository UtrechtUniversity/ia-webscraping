import argparse
import boto3
import pandas as pd


def parse_arguments():
    # parse arguments if available
    parser = argparse.ArgumentParser(
        description='SQS reader'
    )

    # File path to the data.
    parser.add_argument(
        '--queue-url',
        type=str,
        help='url of AWS SQS queue'
    )

    parser.add_argument(
        '--output',
        type=str,
        default='sqs.csv',
        help='path of output csv file'
    )

    parser.add_argument(
        '--keep-messages',
        type=int,
        default=1,
        help='keep messages in queue after exporting, 1: True, 0: False'
    )

    return parser


def get_messages_from_queue(queue_url, keep_messages=True):
    # sqs client
    sqs_client = boto3.client('sqs')

    while True:
        resp = sqs_client.receive_message(
            QueueUrl=queue_url,
            AttributeNames=['All'],
            MaxNumberOfMessages=10
        )

        try:
            yield from resp['Messages']
        except KeyError:
            return

        entries = [
            {'Id': msg['MessageId'], 'ReceiptHandle': msg['ReceiptHandle']}
            for msg in resp['Messages']
        ]

        if keep_messages == False:

            resp = sqs_client.delete_message_batch(
                QueueUrl=queue_url, Entries=entries
            )

            if len(resp['Successful']) != len(entries):
                raise RuntimeError(
                    f"Failed to delete messages: entries={entries!r} resp={resp!r}"
                )


if __name__ == '__main__':

    # example
    # python export_sqs_queue.py --queue-url https://sqs.eu-central-1.amazonaws.com/080708105962/not_scraped --keep-messages 1
    
    # get arguments
    parser = parse_arguments()
    args = vars(parser.parse_args())

    if args['queue_url'] is None:
        raise Exception('No URL was provided')

    keep_messages = False if (args['keep_messages'] == 0) else True

    # setup client 
    boto3.setup_default_session(profile_name='crunch')
    
    collected = []

    for message in get_messages_from_queue(args['queue_url'], keep_messages):
        record = {
            'MessageId': message['MessageId'],
            'SentTimestamp': message['Attributes']['SentTimestamp'],
            'url': message['Body']['url'],
            'reason': message['Body']['reason']
        }
        collected.append(record)

    df = pd.DataFrame(collected)
    df.to_csv(args['output'], index=False)



