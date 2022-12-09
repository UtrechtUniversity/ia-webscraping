import boto3
import json
import os
import re
import aiohttp
import asyncio
import logging
import datetime
import itertools
from urllib.parse import urlparse
from urllib.error import URLError

logger = logging.getLogger()

if os.environ.get("cdx_logging_level", "error") == "info":
    logger.setLevel(logging.INFO)
else:
    logger.setLevel(logging.ERROR)

BLACKLIST_EXTENSIONS = [
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
    ".xls",
    ".xlsx",
    ".pps",
    ".ppsx",
    ".ogv",
    ".zip",
    ".glb",
    ".webm",
    ".webp",
    "robots.txt",
    "/wp-json",
    "/feed$",
]

blacklist = [re.compile(ext + r"(\/|\?|$)", re.IGNORECASE) for ext
             in BLACKLIST_EXTENSIONS]

sqs_message_author = os.environ.get("sqs_message_author", "author")
sqs_cdx_max_messages = int(os.environ.get("sqs_cdx_max_messages", 10))
cdx_lambda_n_iterations = int(os.environ.get("cdx_lambda_n_iterations", 2))
match_exact_url = int(os.environ.get("match_exact_url", 0)) == 1
payload_from_year = os.environ.get("payload_from_year", "2018")
payload_to_year = os.environ.get("payload_to_year", "2019")
url_limit_per_domain = int(os.environ.get("url_limit_per_domain", 1000))

sqs = boto3.resource("sqs")
fetch_sqs_queue = sqs.Queue(os.environ.get("sqs_fetch_id", None))
cdx_sqs_queue = sqs.Queue(os.environ.get("sqs_cdx_id", None))


def get_cdx_sqs_messages():
    return cdx_sqs_queue.receive_messages(
        AttributeNames=["SentTimestamp"],
        MaxNumberOfMessages=sqs_cdx_max_messages,
        MessageAttributeNames=["All"],
        VisibilityTimeout=3,
        WaitTimeSeconds=3,
    )


def get_domain(url):
    try:
        parsed = urlparse(url)
        if len(parsed.scheme) == 0:
            domain = urlparse(f"https://{url}").netloc
        else:
            domain = urlparse(url).netloc
        domain = domain.replace("www.", "")
        return domain
    except URLError as e:
        logger.warning("Not a valid url: %s", e)
        pass


async def get_urls_async(messages):
    tasks = []
    async with aiohttp.ClientSession() as session:
        for message in messages:
            domain = get_domain(message.body)
            first_stage_only = False
            job_tag = ""
            year_window = None
            url_cap = None

            if 'FirstStageOnly' in message.message_attributes:
                first_stage_only = message.message_attributes['FirstStageOnly']['StringValue'] == 'y'

            if 'JobTag' in message.message_attributes:
                job_tag = message.message_attributes['JobTag']['StringValue']

            if 'YearWindow' in message.message_attributes:
                year_window = message.message_attributes['YearWindow']['StringValue'].split(':')

            if 'UrlCap' in message.message_attributes:
                url_cap = int(message.message_attributes['UrlCap']['StringValue'])

            tasks.append(asyncio.ensure_future(get_urls(
                sqs_message_id=message.message_id,
                sqs_receipt_handle=message.receipt_handle,
                domain=domain,
                session=session,
                job_tag=job_tag,
                first_stage_only=first_stage_only,
                year_window=year_window,
                url_cap=url_cap)))

        task_results = await asyncio.gather(*tasks)

    return task_results


async def get_urls(sqs_message_id, sqs_receipt_handle, domain, session,
                   job_tag, first_stage_only, year_window, url_cap):
    # https://github.com/internetarchive/wayback/blob/master/wayback-cdx-server/README.md

    if year_window:
        # if specific time window is present, use that
        year_from = year_window[0]
        year_to = year_window[1]
    else:
        # else use the global settings
        year_from = payload_from_year
        year_to = payload_to_year

    payload = {
        "url": domain,
        "matchType": "prefix",
        "fl": "urlkey,timestamp,digest,original",
        "collapse": "timestamp:4",
        "from": year_from,
        "to": year_to,
        "filter": "statuscode:200",
        "output": "json",
        "showResumeKey": "true",
    }

    if match_exact_url:
        payload["matchType"] = "exact"

    ret = {
        "sqs_message_id": sqs_message_id,
        "sqs_receipt_handle": sqs_receipt_handle,
        "domain": domain,
        "job_tag": job_tag,
        "year_window": [year_from, year_to],
        "first_stage_only": first_stage_only,
        "url_cap": url_cap,
        "urls": None,
        "error": None
    }

    try:
        async with session.get("http://web.archive.org/cdx/search/cdx",
                               params=payload) as response:
            if response.status != 200:
                ret["error"] = f"API returned http-status {response.status} " + \
                               f"for {domain}"
                return ret

            response_list = await response.json()
    except Exception as e:
        logger.warning(f"error while getting {domain}: {str(e)}")
        response_list = None

    if response_list:
        # remove empty elements and first header row
        ret["urls"] = [x for x in response_list if len(x) > 0][1:]

    return ret


def filter_urls(records):
    # Restore original domain in CDX url
    rec_list = [[re.sub(r'http(s)?:\/\/(www\.)?', '', original,
                flags=re.IGNORECASE), time, dgst] for url, time, dgst,
                original in records]

    # sort on timestamp in reversed order => make sure the oldest pages
    # are to be found in the end. With identical digests, the oldest
    # version will be picked in the rec_filtered dictionary
    rec_list = sorted(rec_list, key=lambda item: item[1], reverse=True)

    # filter out unwanted urls and identical pages
    rec_filtered = {}
    for [url, time, dgst] in rec_list:
        if dgst not in rec_filtered.keys() and \
           not any([bool(r.search(url)) for r in blacklist]):
            rec_filtered[dgst] = [url, time]

    return rec_filtered


def send_urls_to_fetch_sqs_queue(job_tag, domain, urls, dry_run):
    messages_sent = 0
    batch_messages = []
    for index, (_, rec) in enumerate(urls.items()):
        [url, timestamp] = rec

        # send messages to scraper queue 10 at a time,
        # unless they're part of a dry run
        if len(batch_messages) == 10:
            if not dry_run:
                sqs_send_message_batch(batch_messages)
            messages_sent += len(batch_messages)
            batch_messages = []

        batch_messages.append(
            {
                "Id": str(index),
                "MessageBody": json.dumps(
                    {
                        "url": f"http://web.archive.org/web/{timestamp}/{url}",
                        "domain": domain
                    }
                ),
                "DelaySeconds": 0,
                "MessageAttributes": {
                    "Author": {
                        "DataType": "String",
                        "StringValue": sqs_message_author
                    },
                    "JobTag": {
                        "DataType": "String",
                        "StringValue": job_tag
                    }
                }
            }
        )

    # send whatever's left to the scrape queue
    if len(batch_messages) > 0:
        if not dry_run:
            sqs_send_message_batch(batch_messages)

        messages_sent += len(batch_messages)

    if dry_run:
        logger.info(f"[{job_tag}]: saw {messages_sent} URLs for " +
                    f" {domain} [dry run]")
    else:
        logger.info(f"[{job_tag}]: sent {messages_sent} URLs to " +
                    f"fetch queue for {domain}")


def sqs_send_message_batch(messages):
    response = fetch_sqs_queue.send_messages(Entries=messages)
    if response.get("Failed"):
        logger.warning('Failed to send the following messages to SQS: ' +
                     f'{str(response["Failed"])}')


def chunks(L, n):
    """ Yield successive n-sized chunks from L """
    for i in range(0, len(L), n):
        yield L[i: i + n]


def delete_processed_messages(processed_messages):
    for batch in chunks(processed_messages, 10):
        cdx_sqs_queue.delete_messages(Entries=batch)


def process_batch(run_id, batch_number):
    # get messages from CDX Queue (one message = one domain)
    messages = get_cdx_sqs_messages()

    if not messages:
        return 0

    logger.info(f"Got {len(messages)} messages from CDX queue ({run_id}:" +
                f"{batch_number+1})")

    processed_messages = []

    # get URLs from internet archive (async)
    task_results = asyncio.run(get_urls_async(messages))

    # process results
    for result in task_results:
        processed_messages.append(process_result(result))

    delete_processed_messages(processed_messages)
    return len(processed_messages)


def process_result(result):
    preTruncLen = 0
    filteredUrls = []

    if result["urls"] is None:
        result["urls"] = []
        if "error" in result and result["error"] is not None and len(result["error"]) > 0:
            logger.warning(f'{result["error"]} ({result["job_tag"]})')
        # else:
        #     print(f'[CDX_INFO] {result["job_tag"]},{result["domain"]},' +
        #           'returned 0 URLs')
    else:
        # filter out URLs with blacklisted extensions
        filteredUrls = filter_urls(result["urls"])

        # if len(filteredUrls) == 0:
        #     print(f'[CDX_INFO] {result["job_tag"]},{result["domain"]},' +
        #           'retained 0 URLs after filtering')
        # else:
        if len(filteredUrls) > 0:
            preTruncLen = len(filteredUrls)

            if result["url_cap"]:
                # cap from CDX message
                url_cap = result["url_cap"]
            elif url_limit_per_domain > 0:
                # cap from general setting
                url_cap = url_limit_per_domain
            else:
                url_cap = 0

            # if more URLs are returned than the limit, sort the URLs by their
            # length ascendingly, so we retain the shortest ones, then slice it
            if url_cap > 0 and preTruncLen > url_cap:
                sortedBySize = \
                    dict(sorted(filteredUrls.items(),
                         key=lambda x: len(x[1][0])))
                filteredUrls = \
                    dict(itertools.islice(sortedBySize.items(),
                         url_cap))
                # print(f'[CDX_INFO] {result["job_tag"]},' +
                #       f'{result["domain"]},truncated {preTruncLen} ' +
                #       f'URLs to {url_cap}')

            # send what's left after filtering/limiting to the queue
            send_urls_to_fetch_sqs_queue(job_tag=result["job_tag"],
                                         domain=result["domain"],
                                         urls=filteredUrls,
                                         dry_run=result['first_stage_only'])

    print(f'[CDX_METRIC] {result["job_tag"]},{result["domain"]},' +
          f'{result["year_window"][0]},{result["year_window"][1]},' +
          f'{len(result["urls"])},{preTruncLen},' +
          f'{len(filteredUrls)}')

    return ({
        "Id": result["sqs_message_id"],
        "ReceiptHandle": result["sqs_receipt_handle"]
    })


def handler(event, context):
    run_id = datetime.datetime.now().strftime('%Y%m%d%H%M')
    logger.info(f"Started CDX Lambda ({run_id})")
    total_proccessed_messages = 0

    for batch_number in range(cdx_lambda_n_iterations):
        total_proccessed_messages += process_batch(run_id, batch_number)

    logger.info(f"Messages processed: {total_proccessed_messages}")
    logger.info(f"End CDX Lambda ({run_id})")


def main():
    """Test script to run from command line"""

    message = (
        "http://kochabo.de,"
        "http://www.usound.com/,"
        "https://www.bsurance.tech,"
        "https://www.checkyeti.com,"
        "http://parkbob.com,"
        "https://playerhunter.com/,"
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
    main()
