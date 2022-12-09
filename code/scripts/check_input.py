from urllib.parse import urlparse
import argparse, re, validators, collections, os, csv
import pandas as pd
from datetime import datetime

class InputChecker:

    infile = None
    csv_header_urls = 'Website'
    csv_header_years = 'Year'
    valid_urls = []
    invalid_urls = []
    without_schema = []
    netlocs = []
    netloc_doubles = []
    no_schema_doubles = []
    bad_years = []

    def setInfile(self,infile):
        self.infile = infile

    def readInfile(self):
        self.urls = pd.read_csv(self.infile, dtype=str)

        if not self.csv_header_urls in self.urls.columns:
            raise ValueError(f"Header '{self.csv_header_urls}' is missing from infile.")

        print(f"Got {len(self.urls):,d} URLs")

        self.includes_year = self.csv_header_years in self.urls.columns

        print(f"Data has {'' if self.includes_year else 'no'} year column")

    def validateURLs(self):
        print("Validating URLs")

        for index, row in self.urls.iterrows():
            url = row[self.csv_header_urls].strip()

            if not validators.url(url):
                self.invalid_urls.append(url)
            else:
                self.valid_urls.append(url)

    def validateYears(self):
        if not self.includes_year:
            return

        print("Validating years")

        for index, row in self.urls.iterrows():

            url = row[self.csv_header_urls].strip()
            year = str(row[self.csv_header_years])

            if len(year)==0:
                self.bad_years.append([url,year,"empty year"])
            elif not year.isdigit():
                self.bad_years.append([url,year,"not a valid year"])
            elif int(year) < 1989:
                # Tim Berners-Lee invented the World Wide Web while working at CERN in 1989
                self.bad_years.append([url,year,"too long ago (<1989)"])
            elif int(year) > int(datetime.now().year):
                self.bad_years.append([url,year,"future date"])

    def findDoubles(self):
        print("Finding doubles")
        for url in self.valid_urls:
            # remove http(s)://www(2).
            cleaned = re.sub('(http(s)?:\/\/)?(www((\d){1})?\.)?','',url,re.IGNORECASE)
            bits = urlparse(f"https://{cleaned}")

            if len(bits.netloc)==0:
                print(f"{url}: no netloc!?")
            else:
                self.netlocs.append(bits.netloc.lower())

            if cleaned.lower().strip("/") != bits.netloc.lower():
                self.without_schema.append(cleaned)

            # if not len(bits.path)==0 and not bits.path=="/":
            #     print(f"has path: {url}")
            #
            # if not len(bits.params)==0:
            #     print(f"has params: {url}")
            #
            # if not len(bits.query)==0:
            #     print(f"has query: {url}")
            #
            # if not len(bits.fragment)==0:
            #     print(f"has fragment: {url}")


        netloc_counter = collections.Counter(self.netlocs)
        self.netloc_doubles = [(x,netloc_counter[x]) for x in netloc_counter if netloc_counter[x]>1]

        no_schema_counter = collections.Counter(self.without_schema)
        self.no_schema_doubles = [(x,no_schema_counter[x]) for x in no_schema_counter if no_schema_counter[x]>1]

    def report(self):
        print(f"invalid: {len(self.invalid_urls):,d}")
        print(f"multiple domains: {len(self.netloc_doubles):,d}; total {sum([x[1] for x in self.netloc_doubles])} URLs")
        print(f"multiple input: {len(self.no_schema_doubles):,d}; total {sum([x[1] for x in self.no_schema_doubles])} URLs")
        if self.includes_year:
            print(f"bad years: {len(self.bad_years):,d}")

    def write_files(self):
        file,ext = os.path.splitext(self.infile)

        if len(self.invalid_urls) > 0:
            with open(f"{file}--invalid{ext}", 'w') as f:
                writer = csv.writer(f)
                for row in self.invalid_urls:
                    writer.writerow([row])

            print(f"wrote '{file}--invalid{ext}'")

        if (len(self.netloc_doubles) > 0) or (len(self.no_schema_doubles) > 0):
            with open(f"{file}--doubles{ext}", 'w') as f:
                writer = csv.writer(f)
                for row in self.netloc_doubles:
                    writer.writerow(row)
                for row in self.no_schema_doubles:
                    writer.writerow(row)

            print(f"wrote '{file}--multiples{ext}'")

        if len(self.bad_years) > 0:
            with open(f"{file}--bad_years{ext}", 'w') as f:
                writer = csv.writer(f)
                for row in self.bad_years:
                    writer.writerow(row)

            print(f"wrote '{file}--bad_years{ext}'")

def main():

    ic = InputChecker()

    parser = argparse.ArgumentParser(description='Fill SQS queue with URLs for which CDX records should be fetched')
    parser.add_argument("--infile", "-f", help=f"Path to CSV-file with URLs (should be in column with header '{ic.csv_header_urls}')",required=True)
    args = parser.parse_args()

    if args.infile == None:
        print("Need an input file (--infile <filename>)")
        exit()

    ic.setInfile(args.infile)
    ic.readInfile()
    ic.validateURLs()
    ic.validateYears()
    ic.findDoubles()
    ic.report()
    ic.write_files()

if __name__ == "__main__":
    main()
