import boto3
import csv
import json
import os
import re
import aiohttp
import asyncio
import logging
from time import perf_counter
import s3fs
from typing import List

from urllib.parse import urlparse
from urllib.error import URLError

# logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger()
if os.environ.get("cdx_logging_level", "error") == "info":
    logger.setLevel(logging.INFO)
else:
    logger.setLevel(logging.ERROR)

EXTENSIONS = [
    ".css",
    ".js",
    ".map",
    ".xml",
    ".png",
    ".woff",
    ".gif",
    ".jpg",
    "eot",
    ".jpeg",
    ".bmp",
    ".mp4",
    ".svg",
    "woff2",
    ".ico",
    ".ttf",
    ".pdf",
    "robots.txt",
    "/wp-json",
    "/feed$",
]

BLACKLIST = [re.compile(ext + r"(\/|\?|$)", re.IGNORECASE) for ext in EXTENSIONS]

TARGET_BUCKET = os.environ.get("target_bucket_id", None)
CDX_METRICS_KEY = os.environ.get("cdx_metrics_file", "crunchbase-cdx-metrics")

# SQS_FETCH_LIMIT: max number of allowed messages in Fetch queue;
# if reached, temporarily stop cdx lambda function
SQS_FETCH_LIMIT = int(os.environ.get("sqs_fetch_limit", 1000))
# SQS_MESSAGE_DELAY_INCREASE:
# the delay time (sec) that should be added to
# every batch of 30 sqs fetch messages
SQS_MESSAGE_DELAY_INCREASE = int(os.environ.get("sqs_message_delay_increase", 10))
# SQS_CDX_MAX_MESSAGES:
# the max number of messages received from the CDX SQS queue in 1 iteration
SQS_CDX_MAX_MESSAGES = int(os.environ.get("sqs_cdx_max_messages", 10))
# CDX_LAMBDA_N_ITERATIONS: the number of iterations the CDX function runs (default=2)
#   every iteration the function:
#       - checks SQS_fETCH_LIMIT
#       - get messages from CDX queue (max: SQS_CDX_MAX_MESSAGES)
#       - get urls from internet archive
#       - filter urls
#       - send urls to fetch queue
#       - delete messages from CDX queue
CDX_LAMBDA_N_ITERATIONS = int(os.environ.get("cdx_lambda_n_iterations", 2))
# RUN_NUMBER: the ID of the crunchbase scrape run;
# this will be added as identifier to the cdx metrics logged in S3
CDX_RUN_ID = int(os.environ.get("cdx_run_id", 1))

# Define queues as SQS resource
sqs = boto3.resource("sqs")
fetch_sqs_queue = sqs.Queue(
    os.environ.get(
        "sqs_fetch_id",
        None,
    )
)
cdx_sqs_queue = sqs.Queue(
    os.environ.get(
        "sqs_cdx_id",
        None,
    )
)

def fetch_queue_limit_reached():
    # Total number of messages in fetch queue
    # = visible message + delayed messages
    local_fetch_sqs_queue = sqs.Queue(
        os.environ.get(
            "sqs_fetch_id",
            None,
        )
    )
    return (
        int(local_fetch_sqs_queue.attributes.get("ApproximateNumberOfMessages"))
        + int(local_fetch_sqs_queue.attributes.get("ApproximateNumberOfMessagesDelayed"))
        > SQS_FETCH_LIMIT
    )


def get_cdx_sqs_messages():
    response = cdx_sqs_queue.receive_messages(
        AttributeNames=["SentTimestamp"],
        MaxNumberOfMessages=SQS_CDX_MAX_MESSAGES,
        MessageAttributeNames=["All"],
        VisibilityTimeout=3,
        WaitTimeSeconds=3,
    )

    logger.info("Received '%d' sqs messages from cdx queue", len(response))
    return response


def get_domain(url):
    try:
        domain = urlparse(url).netloc
        domain = domain.replace("www.", "")
        return domain
    except URLError as e:
        logger.error("Not a valid url: %s", e)
        pass


async def get_urls_async(messages):
    tasks = []
    async with aiohttp.ClientSession() as session:
        for message in messages:
            url = message.body
            domain = get_domain(url)
            task = asyncio.ensure_future(
                get_urls(message.message_id, message.receipt_handle, domain, session)
            )
            tasks.append(task)
        task_results = await asyncio.gather(*tasks)
    return task_results


async def get_urls(sqs_message_id, sqs_receipt_handle, domain, session):
    payload = {
        "url": domain,
        "matchType": "prefix",
        "fl": "urlkey,timestamp,digest",
        "collapse": "timestamp:4",
        "from": os.environ.get("payload_from_year", "2018"),
        "to": os.environ.get("payload_to_year", "2019"),
        "filter": "statuscode:200",
        # 'showDupeCount': 'true',
        # 'showSkipCount': 'true',
        # 'limit': '4',
        "output": "json",
        "showResumeKey": "true",
    }

    ret = {
        "sqs_message_id": sqs_message_id,
        "sqs_receipt_handle": sqs_receipt_handle,
        "domain": domain,
        "urls": None,
        "error": None,
    }

    async with session.get(
        "http://web.archive.org/cdx/search/cdx", params=payload
    ) as response:
        if response.status != 200:
            err_message = (
                "Failed to retrieve records for '%s';"
                + " received errorcode '%d' from internet archive"
            )
            logger.error(
                err_message,
                domain,
                response.status,
            )
            ret["error"] = (
                "Internet archive returned error "
                + f"'{response.status}' for domain '{domain}'"
            )
            return ret
        response_list = await response.json()

    if response_list:
        if not response_list[-2]:
            # The before last one is always empty -> -2
            urls = response_list[1:-2]
        else:
            urls = response_list[1:]
        ret["urls"] = urls
    else:
        logger.warning("No records available for '%s'", domain)
        ret[
            "error"
        ] = f"'0' records returned from internet archive for domain '{domain}'"

    return ret


def restore_domain(domain, url):
    """Restore original domain name in CDX url"""
    domain_split = domain.split(".")
    domain_split.reverse()
    domain_key = ",".join(domain_split) + ")"

    new = url.replace(domain_key, domain).strip()

    return new


def filter_urls(domain, records):
    # Restore original domain in CDX url
    rec_list = [
        [restore_domain(domain, url), time, dgst] for url, time, dgst in records
    ]

    # sort on timestamp in reversed order => make sure the oldest pages
    # are to be found in the end. With identical digests, the oldest
    # version will be picked in the rec_filtered dictionary
    rec_list = sorted(rec_list, key=lambda item: item[1], reverse=True)

    # filter out unwanted urls and identical pages
    rec_filtered = {}
    for [url, time, dgst] in rec_list:
        if dgst not in rec_filtered.keys() and not any(
            [bool(r.search(url)) for r in BLACKLIST]
        ):

            rec_filtered[dgst] = [url, time]

    return rec_filtered


def send_urls_to_fetch_sqs_queue(domain, urls, delay_offset=0):
    messages_send = 0
    batch_messages = []
    for index, (_, rec) in enumerate(urls.items()):
        [url, timestamp] = rec
        file_name = (f"{url}.{timestamp}.txt").replace("/", "_")

        if len(batch_messages) == 10:
            # Max batch size (N=10) reached; send batch
            sqs_send_message_batch(batch_messages)
            batch_messages = []
            messages_send += 10
            if (delay_offset < 900) and (messages_send % 30 == 0):
                # for every 30 messages send;
                # increase message delay until 900 (max allowed value)
                delay_offset += SQS_MESSAGE_DELAY_INCREASE

        batch_messages.append(
            {
                "Id": str(index),
                # every message in a batch must have a unique ID;
                # use index for this
                "MessageBody": json.dumps(
                    {
                        "url": f"http://web.archive.org/web/{timestamp}/{url}",
                        "file_name": file_name,
                        "bucket_name": TARGET_BUCKET,
                    }
                ),
                "DelaySeconds": delay_offset,
                "MessageAttributes": {
                    "Title": {"DataType": "String", "StringValue": "Message nr "},
                    "Author": {"DataType": "String", "StringValue": "mvos"},
                },
            }
        )

    # Send last messages to SQS
    if len(batch_messages) > 0:
        sqs_send_message_batch(batch_messages)
    return delay_offset


def sqs_send_message_batch(messages):
    response = fetch_sqs_queue.send_messages(Entries=messages)
    if response.get("Failed"):
        logger.error(
            "Failed to send the following messages to SQS: '%s'",
            str(response["Failed"]),
        )


def chunks(L, n):
    """ Yield successive n-sized chunks from L """
    for i in range(0, len(L), n):
        yield L[i : i + n]


def handle_domain_no_records(domain, error):
    logger.info("no records for domain '%s'", domain)
    if error:
        logger.info("%s", error)


def handler(event, context):
    logger.info("Started CDX Lambda")
    total_proccessed_messages = 0

    s3_bucket = TARGET_BUCKET
    s3_key = CDX_METRICS_KEY
    columns = ["run", "domain", "n_urls", "n_filtered_urls"]
    cdx_metrics = metrics(s3_bucket=s3_bucket, s3_key=s3_key, columns=columns, logger=logger)

    for i in range(CDX_LAMBDA_N_ITERATIONS):
        logger.info("CDX Lambda run '%d'", i + 1)
        # Check number of messages in Fetch queue
        if fetch_queue_limit_reached():
            info_message = (
                "Number of messages in fetch sqs queue"
                + " higher than limit of '%d'; early return"
            )
            logger.info(
                info_message,
                SQS_FETCH_LIMIT,
            )
            return

        # get messages from CDX Queue
        messages = get_cdx_sqs_messages()
        if not messages:
            # No more messages to process; early return
            break

        # get Urls from internet archive (async)
        task_results = asyncio.run(get_urls_async(messages))

        # Filter urls, send filtered urls to sqs
        processed_messages = []
        # The length of time, in seconds,
        # for which a specific message is delayed
        # before visible in the SQS queue
        delay_offset = 0
        for result in task_results:

            if result["urls"] is None:
                handle_domain_no_records(result["domain"], result["error"])
                cdx_metrics.log(
                    {
                        "run": CDX_RUN_ID,
                        "domain": result["domain"],
                        "n_urls": 0,
                        "n_filtered_urls": 0,
                    }
                )
                continue
            else:
                # Send filtered urls to fetch SQS queue
                filteredUrls = filter_urls(result["domain"], result["urls"])
                delay_offset = send_urls_to_fetch_sqs_queue(
                    result["domain"], filteredUrls, delay_offset
                )

            cdx_metrics.log(
                {
                    "run": CDX_RUN_ID,
                    "domain": result["domain"],
                    "n_urls": len(result["urls"]),
                    "n_filtered_urls": len(filteredUrls),
                }
            )

            processed_messages.append(
                {
                    "Id": result["sqs_message_id"],
                    "ReceiptHandle": result["sqs_receipt_handle"],
                }
            )

        # Delete processed SQS messages CDX queue in batches of 10
        for proc_messages_batch in chunks(processed_messages, 10):
            cdx_sqs_queue.delete_messages(Entries=proc_messages_batch)

        total_proccessed_messages += len(processed_messages)

    logger.info(
        "Number of CDX SQS messages processed: '%d'; Delete messages from CDX SQS",
        total_proccessed_messages,
    )

    cdx_metrics.write_to_s3()

    logger.info("End CDX Lambda")


class metrics(object):
    def __init__(
        self, s3_bucket: str, s3_key, columns: List[str], logger: logging.Logger
    ) -> None:
        self.data: List[dict] = []
        self.columns: List[str] = columns
        self.s3_bucket = s3_bucket
        self.s3_key = s3_key
        self.s3 = s3fs.S3FileSystem(anon=False)
        self.metrics_file = os.path.join(self.s3_bucket, self.s3_key)
        self.logger = logger

    def log(self, metrics: dict):
        """ Add metrics to object """
        # Check metrics schema
        if all(column in metrics for column in self.columns):
            self.data.append(metrics)
        else:
            self.logger.error(f"columns in metrics do not match: {str(metrics)}")

    def write_to_s3(self):
        """Write metrics to S3 as csv file
           Add headers if no object exists
        """
        write_header = (not self.s3.exists(self.metrics_file))
        with self.s3.open(self.metrics_file, "a") as metrics_file:
            current_out_writer = csv.DictWriter(metrics_file, fieldnames=self.columns)
            if write_header:
                # Add header if file does not exists (i.e. new file).
                current_out_writer.writeheader()
            for line in self.data:
                current_out_writer.writerow(line)
        self.data = []


def main():
    """Test script to run from command line"""

    message = (
        "http://kochabo.de,"
        # "http://kochabo.de;;;;;;'myfly.cc'"
        "http://www.usound.com/,"
        # "https://www.bikemap.net,"
        "https://www.bsurance.tech,"
        "https://www.checkyeti.com,"
        "http://parkbob.com,"
        "https://playerhunter.com/,"
        # "https://www.derbrutkasten.com,"
        "https://www.oktav.com,"
        "http://www.healcloud.com,"
        "https://www.involve.me"
    )

    urls = message.split(",")
    message_id = 0
    batch_messages = []
    for url in urls:
        # send messages to sqs
        message_id += 1
        batch_messages.append(
            {"Id": str(message_id), "MessageBody": url, "DelaySeconds": 0}
        )
    cdx_sqs_queue.send_messages(Entries=batch_messages)

    handler(None, None)


if __name__ == "__main__":
    tic = perf_counter()
    main()

    toc = perf_counter()
    print(f"Program runtime {toc - tic:0.4f} seconds")
