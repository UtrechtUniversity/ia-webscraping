import asyncio
import json
import logging
import os
import re
import time
import random
from urllib.parse import urlparse
from datetime import datetime
from bs4 import BeautifulSoup
from aiohttp import ClientSession
import boto3

kinesis_firehose_stream = "scrape-kinesis-firehose"

formats_to_save = os.environ.get("formats_to_save", "txt,links").split(",")

logger = logging.getLogger()

if os.environ.get("scraper_logging_level", "error") == "info":
    logger.setLevel(logging.INFO)
else:
    logger.setLevel(logging.ERROR)


def make_kinesis_record(job_tag, domain, url, text=False, links=False):
    if not text and not links:
        return None

    record = {
        "domain": domain,
        "url": url,
        "job_tag": job_tag,
        "timestamp": datetime.now().isoformat()
    }

    record["page_text"] = text if text else ""
    record["page_links"] = links if links else ""

    original_size = 0

    while True:

        size = len(json.dumps(record))

        if original_size == 0:
            original_size = size

        kinesis_max_record_size = 1e6

        if size <= kinesis_max_record_size:
            break

        pre_size = len(str(record["page_text"])+str(record["page_links"]))

        if record["page_text"] and record["page_links"]:
            if len(record["page_text"]) > len(record["page_links"]):
                record["page_text"] = "\n".join(record["page_text"].split()[:-1])
            else:
                record["page_links"] = "\n".join(record["page_links"].split()[:-1])
        elif record["page_text"]:
            record["page_text"] = "\n".join(record["page_text"].split()[:-1])
        elif record["page_links"]:
            record["page_links"] = "\n".join(record["page_links"].split()[:-1])

        if pre_size <= len(str(record["page_text"])+str(record["page_links"])):
            break

    if size != original_size:
        logger.warning(f"{job_tag},{url}: kinesis message truncated " +
                     f"from {size} to {original_size}")

    return {'Data': json.dumps(record) + '\n'}


def remove_internet_archive_url(url, keep_archived_protocol=False):
    # remove:
    # - http(s)
    # - web.archive.org
    # - generic bit of the path ('/web/1234567890/')
    re_ia_link = r'^http(s?):\/\/web.archive.org\/web\/(\d)+\/'
    # - optional http(s) at the beginning of the archived domain
    re_archived_protocol = r'(http(s?):\/\/)?'

    if keep_archived_protocol:
        return re.sub(re_ia_link, '', str(url))

    return re.sub(re_ia_link+re_archived_protocol, '', str(url))


def clean_html(response):
    """strips svg / script / style tags"""
    # remove svg
    response = re.sub(r'<svg[\s\S]+?/svg>', '', response)
    # remove script
    response = re.sub(r'<script[\s\S]+?/script>', '', response)
    # remove style
    response = re.sub(r'<style[\s\S]+?/style>', '', response)
    # return
    return response


async def fetch(message, session, output_buffer, processed_messages):
    data = json.loads(message['body'])
    domain = data['domain']
    url = data['url']

    if 'JobTag' in message['messageAttributes']:
        job_tag = message['messageAttributes']['JobTag']['stringValue']
    else:
        job_tag = ""

    logger.info(f'fetch url "{url}"')

    content_text = False
    content_links = False

    try:

        async with session.get(url) as response:

            resp_content = await response.read()

            if response.status == 200:

                try:
                    # resp.content is a byte array, convert to string
                    # raw_contents = resp_content.decode("utf-8", "ignore")
                    try:
                        raw_contents = resp_content.decode("utf-8", "strict")
                    except Exception:
                        raw_contents = resp_content.decode("utf-8", "ignore")

                    if "txt" in formats_to_save or "links" in formats_to_save:
                        contents = clean_html(raw_contents)
                        soup = BeautifulSoup(contents, "html.parser")

                    if "txt" in formats_to_save:
                        content_text = soup.get_text("\n", strip=True)
                        # if len(content_text) == 0:
                        #     print(f"[SCRAPE_INFO] {job_tag},{domain}," +
                        #           f"{data['url']},parsed page body is empty")

                    if "links" in formats_to_save:
                        # extract all <a>-elements
                        doc_links = []
                        for link in soup.findAll("a"):
                            # get each link's href-attribute
                            doc_link = link.get("href")
                            # internet archive links are prepended
                            # to the original links
                            doc_link = remove_internet_archive_url(doc_link,
                                                                   keep_archived_protocol=True)
                            # parse the link to see whether it has a FQDN
                            # (to omit the relative, internal links)
                            parse_link = urlparse(doc_link)
                            if len(parse_link.netloc) > 0:
                                # keep only the full links (netloc contains
                                # the domain) (n.b. seems IA turns *all* links
                                # into full links but we'll leave that to the
                                # customer)
                                doc_links.append(doc_link)

                        if len(doc_links) > 0:
                            content_links = "\n".join(doc_links)
                        # else:
                        #     print(f"[SCRAPE_INFO] {job_tag},{domain}," +
                        #           f"{data['url']},found no links")

                except Exception as e:
                    logger.warning(f'Failed to parse "{url}": {str(e)}')
            else:
                logger.warning(f'Failed to get "{url}": {response.status}')
                    
            # too many requests or server error: do not delete message, try again later
            if response.status == 429 or response.status >= 500:
                logger.warning(f"Server returned {response.status}; retrying {url} later.")
            else:
                record = make_kinesis_record(job_tag=job_tag, domain=domain,
                                            url=url, text=content_text,
                                            links=content_links)

                # record == None if there's no text or links
                if record:
                    output_buffer.append(record)

                size_txt = 0 if not content_text else len(content_text)
                size_links = 0 if not content_links else len(content_links)

                print(f"[SCRAPE_METRIC] {job_tag},{domain},{data['url']}," +
                    f"{str(size_txt)},{str(size_links)}")

                processed_messages = log_processed_message(processed_messages, message)

    except Exception as e:
        logger.warning(f'Failed to fetch "{url}": {str(e)}')
        print(f"[SCRAPE_METRIC] {job_tag},{domain},{data['url']},0,0")
        processed_messages = log_processed_message(processed_messages, message)


def log_processed_message(processed_messages,message):
    processed_messages.append({
        'Id': message['messageId'],
        'ReceiptHandle': message['receiptHandle']
    })
    return processed_messages


async def fetch_all(records, output_buffer, processed_messages):
    tasks = []
    fetch.start_time = dict()
    async with ClientSession() as session:
        for record in records:
            task = asyncio.ensure_future(fetch(record, session, output_buffer,
                                               processed_messages))
            tasks.append(task)
        _ = await asyncio.gather(*tasks)



def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def handler(event, context):
    output_buffer = []
    processed_messages = []

    logger.info(f'scraper lambda received {len(event["Records"])} messages')
    loop = asyncio.get_event_loop()
    future = asyncio.ensure_future(fetch_all(event['Records'],
                                   output_buffer=output_buffer,
                                   processed_messages=processed_messages))
    loop.run_until_complete(future)

    if len(output_buffer) > 0:
        client = boto3.client("firehose", region_name="eu-central-1")

        for output_chunk in chunks(output_buffer, 400):

            response = client.put_record_batch(
                DeliveryStreamName=kinesis_firehose_stream,
                Records=output_chunk
            )

            retries = []

            if 'RequestResponses' in response:
                """For each record, the index of the response element is the same 
                as the index used in the request array."""
                for index, item in enumerate(response['RequestResponses']):
                    if 'ErrorCode' not in item and 'ErrorMessage' not in item:
                        continue
                    # logger.error(f"Firehose Delivery: {item['ErrorMessage']} ({item['ErrorCode']})")
                    if item['ErrorCode'] == 'ServiceUnavailableException' and item['ErrorMessage'] ==  'Slow down.':
                        # retrying messages that were sent to fast
                        retries.append(index)
                    else:
                        print(f"FAILED_KINESIS: {item}")

            if len(retries) > 0:
                secs = random.randint(1, 5)
                print(f"FAILED_KINESIS: retrying {len(retries)} items in {secs}s")
                time.sleep(secs)
                response = client.put_record_batch(
                    DeliveryStreamName=kinesis_firehose_stream,
                    Records=[output_chunk[x] for x in retries]
                )
           
    if len(processed_messages) > 0:
        sqs = boto3.resource("sqs")
        sqs_queue = sqs.Queue(os.environ.get("sqs_fetch_id", None))
        response = sqs_queue.delete_messages(Entries=processed_messages)
        if 'Failed' in response and response['Failed'] > 0:
            logger.warning("delete failed:" +
                         f"{len(response['Failed'])}/{len(processed_messages)} " +
                         "messages; " +
                         f"{list(set([x['Message'] for x in response['Failed']]))}")


if __name__ == '__main__':
    r1 = {
        'domain': 'hexdocs.pm',
        'url': 'https://hexdocs.pm/phoenix_live_view/bindings.html',
        'job_tag': 'test'
    }

    r2 = {
        'domain': 'hexdocs.pm',
        'url': 'https://hexdocs.pm/elixir/Enum.html#reduce/2',
        'job_tag': 'test'
    }

    workload = {
        'Records': [
            {'body': json.dumps(r1)},
            {'body': json.dumps(r2)}
        ]
    }

    handler(workload, None)
