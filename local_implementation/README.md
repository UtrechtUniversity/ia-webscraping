# IA-webscraping: local implementation

These script contain a local implementation of the IA-webscraping pipeline. These do not require AWS infrastructure, and as a result, do not benefit from AWS infrastructure. Everything is done sequentially in a single thread (no parallelisation), so if you have a lot of sites, a lot of patience will be required. Also, the size of your local storage might become a problem if you scrape millions of URLs.

Be aware: this version has not been extensively tested.

## Requirements

+ Python 3.9 or higher
+ [BeautifulSoup](https://pypi.org/project/beautifulsoup4/)

## Pipeline

### Step 1: harvest IA URLs

Typical usage:

```bash
python ia_harvest_urls.py -i links.txt
```
This will read links to be queried from `links.txt` and retrieve the URL for the newest snapshot (if any are avaiulable) form the Internet Archive for each of the links in the file, and save the IA URLs to a JSON-file.

Input file should have one link per line. Empty lines and invalid URLs will be skipped.

All options:
```bash
usage: ia_harvest_urls.py [-h] -i INPUT_FILE [-o OUTPUT_FILE] [-f YEAR_FROM] \
  [-t YEAR_TO] [--get-domain] [--url-limit URL_LIMIT]

optional arguments:
  -h, --help            show this help message and exit
  -i INPUT_FILE, --input-file INPUT_FILE
                        Path to CSV- or text-file with a list of domains.
  -o OUTPUT_FILE, --output-file OUTPUT_FILE
                        Default: ./ia-urls.json
  -f YEAR_FROM, --year-from YEAR_FROM
                        Default: 2020
  -t YEAR_TO, --year-to YEAR_TO
                        Default: 2024
  --get-domain          Retrieve input's TLD, rather than full page URL.
                        Default: False
  --snapshot-limit SNAPSHOT_LIMIT
                        Max number of snapshots per site to harvest (newest first).
                        Default: 1
```

`--get-domain` will have the script retrieve URLs for each link's domain, rather than the full URL. (So for example, `uu.nl` instead of  `https://www.uu.nl/organisatie/nieuws-agenda`).

There is a 1 second delay between subsequent requests to the IA, to avoid overloading the service. If you get `connection refused`-errors, increase the wait time by changing the value of `request_wait` at the top of the `InternetArchiveUrlHarvestrer` class.


#### Resuming harvesting
While downloading, the script keeps track of progress of which links it has finished harvesting snapshots for. If you break off harvesting, and resume later, the script will skip the links it has already processed. When resuming, results are automatically appended to the output file if it is already present. The script keeps track of its progress by writing to a file called `.sites`, located in the same folder as the output file. You can delete or alter the `.sites` file as you see fit to influence the script's behaviour. 

#### URL Match Scope
The script only retrieves **exact matches** of each URL. To change, change `url_match_scope = "exact"` on line 125 of the script to the appropriate value (see [Url Match Scope](https://github.com/internetarchive/wayback/blob/master/wayback-cdx-server/README.md#url-match-scope) in the IA API's documentation). 

Be aware, setting `url_match_scope` to `prefix` will increase the number of pages to be scraped, possibly dramatically so. Also, be aware that the `--snapshot-limit` is enforced on a list of all URLs that is first being sorted by size, shortest first, and then by date.


### Step 2: saving pages
Typical usage:

```bash
python ia_get_pages.py -o /my-download-folder/
```
This will read IA links to be downloaded from the output file of thet first script (default `ia-urls.json`), download them from the Internet Archive, and save them in the specified folder.

All options:
```bash
usage: ia_get_pages.py [-h] -i INPUT_FILE -o OUTPUT_FOLDER

optional arguments:
  -h, --help            show this help message and exit
  -i INPUT_FILE, --input-file INPUT_FILE
  -o OUTPUT_FOLDER, --output-folder OUTPUT_FOLDER

```

The script will download the pages for all the links in the input file, and store them in JSON-files in the output folder. File names will refelect the link it concerns (For example, data for link `https://www.domain.nl/some-page/` will be in a file called `ia-webscrape-data--https___www_domain_nl_some_page.json`).

There is a 1 second delay between subsequent requests to the IA, to avoid overloading the service. If you get `connection refused`-errors, increase the wait time by changing the value of `request_wait` at the top of the `InternetArchivePageGetter` class.


#### Output format
For each link in the original input file, the script will create a JSON-file with the following structure:

```json
[
  {
    "domain": "domain.nl",
    "url": "www.domain.nl/some-page/",
    "timestamp": "20240228135330",
    "ia_url": "http://web.archive.org/web/20240228135330/www.domain.nl/some-page/",
    "text": "This is the plain text on the retrieved page.",
    "links": [
      "www.domain.nl/home/",
      [...]
    ]
  },
  [...]
]
```
`text` contains all the page's human readable text (all html-elements are removed), `links` contains a list of all hyperlinks found on the page. You can change what is saved by changing the value of `formats_to_save` at the top of the `InternetArchivePageGetter` class (remove either `"txt"` or `"links"`).

Be aware that both text and links will include additional content and hyperlinks added by Internet Archive.


#### Resuming downloading
Like the URL harvester, this script keeps track of its progress to allow resumption. Processed links are kept track of in a file called `.pages`, located in the same folder as the saved files.
