import argparse
import hashlib
import itertools
import json
import logging
import re
import time
import urllib.parse
import urllib.request
from memory_file import MemoryFile
from pathlib import Path
from typing import NamedTuple

BLACKLIST_EXTENSIONS = [
    ".css", ".js", ".map", ".xml", ".png", ".woff", ".gif", ".jpg", "eot",
    ".jpeg",".bmp",".mp4",".svg","woff2",".ico",".ttf",".pdf",".xls", ".xlsx",
    ".pps",".ppsx",".ogv",".zip",".glb",".webm",".webp",
    "robots.txt", "/wp-json", "/feed$",
]

class ValidDomain(NamedTuple):
    line: str
    tld: str

class InternetArchiveUrlHarvester:

    request_delay = 1 # seconds

    def __init__(self,
                 input_file,
                 output_file,
                 year_from,
                 year_to,
                 get_domain = False,
                 snapshot_limit = 1):

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger()

        self.logger.info(f"Year from: {year_from}")
        self.logger.info(f"Year to: {year_to}")
        self.logger.info(f"Get domain instead of URL: {get_domain}")
        self.logger.info(f"Snapshot limit: {snapshot_limit}")

        self.output_file = Path(output_file)

        if self.output_file.is_file():
            self.logger.warning(f"Output file {str(self.output_file)!r} already exists; appending")

        self.memory = MemoryFile(file=self.output_file.parent / Path(".sites"))

        valid_urls, not_valid = self.load_lines(input_file=input_file)
        for item in not_valid:
            self.logger.info(f"Invalid URL: {item!r}")
        self.logger.info(f"{len(valid_urls)} valid URLs")

        self.harvest_urls(valid_urls=valid_urls,
                          year_from=year_from,
                          year_to=year_to,
                          get_domain=get_domain,
                          snapshot_limit=snapshot_limit)

    @staticmethod
    def load_lines(input_file):
        regex = r'(https?://)?(www\d?\.)?(?P<domain>[\w\.-]+\.\w+)(/\S*)?'
        valid = []
        not_valid = []
        with open(input_file, "r") as f:
            for line in [x.strip() for x in f.readlines()]:
                if len(line)==0:
                    continue
                match = re.match(regex, line)
                if match:
                    valid.append(ValidDomain(line, match.group("domain")))
                else:                
                    not_valid.append(line)

        return valid, not_valid

    @staticmethod
    def filter_urls(records):

        blacklist = [re.compile(ext + r"(\/|\?|$)", re.IGNORECASE) for ext
                        in BLACKLIST_EXTENSIONS]

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

    def save_records(self, records):
        if self.output_file.is_file():
            with open(self.output_file, 'r') as f:
                prev = json.load(f)

            records = prev + records
            records = list({x['url']:x for x in records}.values())

        with open(self.output_file, 'w') as f:
            json.dump(records, f)

        self.logger.info(f"Wrote to {str(self.output_file)!r}")

    def harvest_urls(self,
                     valid_urls, 
                     year_from,
                     year_to,
                     get_domain,
                     snapshot_limit = None):

        ia_cdx_url = 'http://web.archive.org/cdx/search/cdx'
        url_match_scope = "exact"

        payload = {
            "url": None,
            "matchType": "prefix",
            "fl": "urlkey,timestamp,digest,original",
            "collapse": "timestamp:4",
            "from": year_from,
            "to": year_to,
            "filter": "statuscode:200",
            "output": "json",
            "showResumeKey": "true",
            "matchType": url_match_scope
        }

        records = []

        for domain in valid_urls:
            
            payload['url'] = domain.tld if get_domain else domain.line

            if self.memory.exists(payload['url']):
                self.logger.info(f"Skipping {payload['url']!r} (retrieved previously)")
                continue

            self.logger.info(f"Retrieving {payload['url']!r}")
            data = urllib.parse.urlencode(payload)
            data = data.encode('ascii') # data should be bytes
            req = urllib.request.Request(ia_cdx_url, data)
            with urllib.request.urlopen(req) as response:
                if response.status != 200:
                    self.logger.error(f"API returned http-status {response.status} for {domain}")
                else:
                    data = json.loads(response.read().decode('utf8'))
                    filtered = self.filter_urls(data)
                    del filtered['digest']
                    filtered = self.enforce_snapshot_limit(filtered_urls=filtered,
                                                           snapshot_limit=snapshot_limit)
                    records.append({
                        'domain': domain.tld,
                        'url': payload['url'],
                        'from': year_from,
                        'to': year_to,
                        'urls': filtered})

                    self.logger.info(f"Got {len(filtered)} record(s)")
            
            self.save_records(records=records)
            self.memory.store(payload['url'])
            time.sleep(self.request_delay)


    @staticmethod
    def enforce_snapshot_limit(filtered_urls, snapshot_limit):
        if len(filtered_urls)==0 or snapshot_limit is None:
            return filtered_urls

        # if more URLs are returned than the limit, sort the URLs by their
        # length ascendingly, so we retain the shortest ones, then slice it
        if snapshot_limit > 0 and len(filtered_urls) > snapshot_limit:
            sorted_by_size = dict(sorted(filtered_urls.items(), key=lambda x: len(x[1][0])))
            filtered_urls = dict(itertools.islice(sorted_by_size.items(), snapshot_limit))

        return filtered_urls

if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input-file", type=str, required=True, 
                        help="""Path to CSV- or text-file with a list of domains.""")
    parser.add_argument("-o", "--output-file", type=str, default="./ia-urls.json", 
                        help="Default: ./ia-urls.json")
    parser.add_argument("-f", "--year-from", type=int, default=2020, 
                        help="Default: 2020")
    parser.add_argument("-t", "--year-to", type=int, default=2024, 
                        help="Default: 2024")
    parser.add_argument("--get-domain", action='store_true', default=False, 
                        help="""Retrieve input's TLD, rather than full page URL.
                        Default: False""")
    parser.add_argument("--snapshot-limit", type=int, default=1,
                        help="""Max number of snapshots per site to harvest (newest first).
                        Default: 1""")

    args = parser.parse_args()

    InternetArchiveUrlHarvester(
        input_file=args.input_file,
        output_file=args.output_file,
        year_from=args.year_from,
        year_to=args.year_to,
        get_domain=args.get_domain,
        snapshot_limit=args.snapshot_limit)
