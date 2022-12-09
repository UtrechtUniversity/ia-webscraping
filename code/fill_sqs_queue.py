import argparse
import boto3
import re
import pandas as pd
from pathlib import Path
from datetime import datetime


class MessageQueuer:

    infile = None
    csv_header_urls = 'Website'
    csv_header_years = 'Year'
    batch_size = 10
    message_batch = []
    delay_seconds = 5
    aws_profile = None
    sqs_queue = None
    sqs_message_author = None
    job_tag = None
    first_stage_only = False
    year_window = None

    def __init__(self, sqs_queue, infile, aws_profile,
                 message_author, job_tag, first_stage_only,
                 year_window):

        if job_tag is None:
            self.job_tag = self.clean_job_tag(self.get_generated_job_tag())
            print(f"Generated job tag: {self.job_tag}")
        else:
            self.job_tag = self.clean_job_tag(job_tag)

        if year_window is not None:
            assert year_window.isdigit(), f"{year_window} is not an integer value"
            self.year_window = int(year_window)

        assert infile is not None, "Need an input file (--infile <filename>)"
        path = Path(infile)
        assert path.is_file(), f"{infile} is not a file"

        cols = [self.csv_header_urls]

        if self.year_window is not None:
            cols.append(self.csv_header_years)

        self.urls = pd.read_csv(path, usecols=cols)
        print(f"Got {len(self.urls):,d} URLs")

        assert sqs_queue is not None, "Need an SQS Queue"
        self.sqs_queue = sqs_queue

        assert aws_profile is not None, "Need a local AWS profile"
        self.aws_profile = aws_profile

        assert message_author is not None, "Need a message author"
        self.sqs_message_author = message_author

        assert type(first_stage_only) == bool, f"{first_stage_only} is not a bool value"
        self.first_stage_only = first_stage_only

    @staticmethod
    def clean_job_tag(job_tag):
        return re.sub(r'[^a-zA-Z0-9!\.\-\_\.\*\'\(\)\#]', '-', job_tag)[:32]

    @staticmethod
    def get_generated_job_tag():
        now = datetime.now()
        return f'{now.year}.{now.month:0>2d}.{now.day:0>2d}-{now.hour:0>2d}.{now.minute:0>2d}'

    def queue_messages(self, message_batch):
        boto3.setup_default_session(profile_name=self.aws_profile)
        sqs = boto3.resource('sqs')
        queue = sqs.get_queue_by_name(QueueName=self.sqs_queue)
        response = queue.send_messages(Entries=message_batch)

        if response.get('Failed'):
            print(f"Failed to send messages to queue: {str(response['Failed'])}")

    def send_urls_to_queue(self):
        print("Sending messages to SQS Queue")
        messages_sent = 0

        for index, row in self.urls.iterrows():
            url = row[self.csv_header_urls]

            year_start = None
            year_end = None

            if self.year_window is not None:
                try:
                    year_start = int(row[self.csv_header_years])
                    year_end = year_start + self.year_window
                except Exception:
                    print(f"Missing year value: {url.strip()}")
                    pass

            if len(self.message_batch) == self.batch_size:
                self.queue_messages(self.message_batch)
                messages_sent += len(self.message_batch)
                self.message_batch = []
                if messages_sent % 1000 == 0:
                    print(f"{messages_sent:>8,d} / {len(self.urls):,d}")

            message = {
                    'Id': str(index),
                    'MessageBody': url.strip(),
                    'DelaySeconds': self.delay_seconds,
                    'MessageAttributes': {
                        'Author': {
                            'DataType': 'String',
                            'StringValue': self.sqs_message_author
                        },
                        'JobTag': {
                            'DataType': 'String',
                            'StringValue': self.job_tag
                        },
                        'FirstStageOnly': {
                            'DataType': 'String',
                            'StringValue': 'y' if self.first_stage_only else 'n'
                        }
                    }
                }

            if year_start and year_end:
                message['MessageAttributes']['YearWindow'] = {
                    'DataType': 'String',
                    'StringValue': f"{year_start}:{year_end}"
                }

            self.message_batch.append(message)

        if len(self.message_batch) > 0:
            self.queue_messages(self.message_batch)
            messages_sent += len(self.message_batch)

        print(f"Sent {messages_sent:,d} messages to {self.sqs_queue}")

    @classmethod
    def from_arguments(cls):
        parser = argparse.ArgumentParser(description="Fill SQS queue with domains for which URLs should be fetched from the Internet Archive")
        parser.add_argument("--sqs-queue", "-q", help="SQS queue name (current default: crunchbase-cdx-queue)", default="crunchbase-cdx-queue")
        parser.add_argument("--infile", "-f", help=f"Path to CSV-file with URLs (should be in column with header '{cls.csv_header_urls}')", required=True)
        parser.add_argument("--aws-profile", "-p", help="AWS profile name (current default: crunch)", default="crunch")
        parser.add_argument("--message-author", "-a", help="Message author name (current default: crunchbase)", default="crunchbase")
        parser.add_argument("--job-tag", "-t", help="Tag to help identify and keep together results from one job (max. 32 characters)")
        parser.add_argument("--year-window", "-y", help=f"Number of years to scrape from start year (requires column '{cls.csv_header_years}' with start year)")
        parser.add_argument("--first-stage-only", action='store_true')
        # always includes start year, so y=4 will give 5 years
        args = parser.parse_args()

        return cls(
            sqs_queue=args.sqs_queue,
            infile=args.infile,
            aws_profile=args.aws_profile,
            message_author=args.message_author,
            job_tag=args.job_tag,
            first_stage_only=args.first_stage_only,
            year_window=args.year_window,
        )


if __name__ == "__main__":
    mq = MessageQueuer.from_arguments()
    mq.send_urls_to_queue()
