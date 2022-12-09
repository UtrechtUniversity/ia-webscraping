import argparse
import boto3
import json


class QueueReader:

    def __init__(self):
        self.sqs_client = boto3.client('sqs')
        self.queues = self.get_queues()
        self.queue = None

    def get_queues(self):
        queues = self.sqs_client.list_queues()
        return [{ "url": x, "short": x.split("/")[-1:][0]} for x in queues['QueueUrls']]

    def set_queue(self, queue):
        tmp = [x for x in self.queues if x["url"] == queue or x["short"] == queue]
        if len(tmp) == 0:
            raise ValueError(f"unknown queue '{queue}'")
        self.queue = tmp[0]
        print(f"Set queue: {self.queue}")

    def get_messages_from_queue(self, delete=False):
        """Generates messages from an SQS queue.

        Note: this continues to generate messages until the queue is empty.
        Every message on the queue will be deleted.

        :param queue_url: URL of the SQS queue to get.
        :param delete: switch for deletion after retrieving.

        Original source:
        https://alexwlchan.net/2018/01/downloading-sqs-queues/

        """

        queue_url = self.queue["url"]

        while True:
            resp = self.sqs_client.receive_message(
                QueueUrl=queue_url,
                AttributeNames=['All'],
                MessageAttributeNames=['job_tag', 'JobTag'],
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

            if delete:
                resp = self.sqs_client.delete_message_batch(
                    QueueUrl=queue_url, Entries=entries
                )

                if len(resp['Successful']) != len(entries):
                    raise RuntimeError(
                        f"Failed to delete messages: entries={entries!r} resp={resp!r}"
                    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sqs-queue", "-q", help="SQS name or URL")
    parser.add_argument("--file", "-f", help="JSONL file to save to (appends)")
    parser.add_argument("--max-messages", "-m", help="Maximum number of messages to retrieve", default=0, type=int)
    parser.add_argument("--delete", action='store_true', help="Delete messages while retrieving")
    args = parser.parse_args()

    qr = QueueReader()
    if not args.sqs_queue:
        print("Available queues:")
        for queue in qr.get_queues():
            print((queue))

        exit()

    qr.set_queue(args.sqs_queue)

    if args.file:
        f = open(args.file,'a')
    else:
        f = None

    n = 0
    for message in qr.get_messages_from_queue(delete=args.delete):
        print(json.dumps(message))
        if f:
            f.write(json.dumps(message))
        n += 1
        if args.max_messages > 0 and n >= args.max_messages:
            break

    print(f"Retrieved {n} messages")
    if f:
        f.close()
        print(f"Wrote to {args.file}")