import argparse
import json
import logging
import re
import time
import urllib.request
from bs4 import BeautifulSoup
from datetime import datetime
from memory_file import MemoryFile
from pathlib import Path
from typing import NamedTuple, List
from urllib.parse import urlparse

class InternetArchivePageGetter:

    request_delay = 1 # seconds
    formats_to_save = ["txt", "links"]

    def __init__(self,
                 input_file,
                 output_folder):

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger()

        self.logger.info(f"Input file: {input_file!r}")
        self.logger.info(f"Output folder: {output_folder!r}")
        self.logger.info(f"Formats to save: {self.formats_to_save}")

        self.output_folder = Path(output_folder)
        self.memory = MemoryFile(file=self.output_folder / Path(".pages"))

        with open(input_file, 'r') as f:
            urls = json.load(f)

        urls = self.add_ia_urls(data=urls)
        self.download_pages(page_urls=urls)

    @staticmethod
    def add_ia_urls(data):
        ia_url = "http://web.archive.org/web/{timestamp}/{url}"
        for item in data:
            ia_urls = []
            for hsh in item['urls']:
                url, timestamp = item['urls'][hsh]
                ia_urls.append((ia_url.format(url=url, timestamp=timestamp), timestamp))

            item.update({'ia_urls': ia_urls})

        return data

    def download_pages(self, page_urls):

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

        for item in page_urls:

            if self.memory.exists(item['url']):
                self.logger.info(f"Skipping {item['url']!r} (retrieved previously)")
                continue
            
            self.logger.info(f"Retrieving pages for {item['url']!r}")
            records = []

            for ia_url, timestamp in item['ia_urls']:

                req = urllib.request.Request(ia_url)

                with urllib.request.urlopen(req) as response:

                    if response.status != 200:
                        self.logger.error(f"API returned http-status {response.status} for {domain}")
                    else:
                        try:
                            raw_contents = response.read().decode("utf-8", "strict")
                        except Exception:
                            raw_contents = response.read().decode("utf-8", "ignore")

                        if "txt" in self.formats_to_save or "links" in self.formats_to_save:
                            contents = clean_html(raw_contents)
                            soup = BeautifulSoup(contents, "html.parser")

                        if "txt" in self.formats_to_save:
                            content_text = soup.get_text("\n", strip=True)

                        if "links" in self.formats_to_save:
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

                            record = {
                                'domain': item['domain'],
                                'url': item['url'],
                                'timestamp': timestamp,
                                'ia_url': ia_url,
                                'text': content_text,
                                'links': list(set(doc_links),)
                            }

                            records.append(record)

                time.sleep(self.request_delay)  

            self.write_output(url=item['url'], records=records)
            self.memory.store(item['url'])


    def write_output(self, url, records):

        output_file_tpl = "ia-webscrape-data--{url}.json"
        output_file = Path(output_file_tpl.format(url=re.sub(r'[^\da-zA-Z]', '_', url)))

        with open(self.output_folder / output_file, 'w+') as f:
            json.dump(records, f)

        self.logger.error(f"Wrote {str(output_file)!r}")

if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input-file", type=str, required=True, default="./ia-urls.json")
    parser.add_argument("-o", "--output-folder", type=str, required=True)
    args = parser.parse_args()

    InternetArchivePageGetter(
        input_file=args.input_file,
        output_folder=args.output_folder,
    )