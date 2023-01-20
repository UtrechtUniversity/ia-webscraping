# ia-webscraping

This repository provides code to set up an AWS workflow for collecting webpages from the Internet Archive.
It was developed for the Crunchbase project to assess the sustainability of European startup-companies by analyzing their websites.

The [workflow](#architecture) is set up to scrape large numbers (millions) of Web pages. With large numbers of http requests from a single location, 
the Internet Archive's response becomes slow and less reliable. We use serverless computing to distribute the process as much as possible.
In addition, we use queueing services to manage the logistics and a data streaming service to process the large amounts of individual files.

Please note that this software is designed for users with prior knowledge of Python, AWS and infrastructure.


## Table of contents

- [Getting started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [Running the pipeline](#running-the-pipeline)
  - [Uploading URLs](#upload-urls-to-be-scraped)
  - [Monitoring progress](#monitor-progress)
- [Results](#results)
  - [Processing Parquet files](#processing-parquet-files)
- [Cleaning up](#cleaning-up)
  - [Deleting the infrastructure](#deleting-the-infrastructure)
  - [Deleting buckets](#deleting-buckets)
- [About the project](#about-the-project)
  - [Architecture](#architecture)
  - [Built with](#built-with)
  - [License and citation](#license-and-citation)
  - [Team](#team)

## Getting started

  - [Prerequisites](#prerequisites)
  - [Installation](#installation)

### Prerequisites
The process includes multiple bash-files that only run on Linux or a Mac.
To run this project you need to take the following steps:
- [Install AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html)
- [Configure AWS CLI credentials](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html); create a local profile with the name 'crunch'
- Install [Python3](https://www.python.org/downloads/), [pip3](https://pypi.org/project/pip/), [pandas](https://pandas.pydata.org/), [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/quickstart.html#installation)
- Install [Terraform](https://www.terraform.io/downloads.html)
- Create a personal S3 bucket in AWS (region: 'eu-central-1'; for other settings defaults suffice). This is the bucket the code for your Lambda-functions will be stored in. Another bucket for the sults will be created automatically.

### IAM Developer Permissions Crunchbase
If you are going to use an IAM account for the pipeline, make sure it has the proper permissions to create buckets, queues and policies, and to create, read and write to log goups and streams. The following [AWS managed policies](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_managed-vs-inline.html) were given to all developers of the original Crunchbase project:
- AmazonEC2FullAccess
- AmazonSQSFullAccess
- IAMFullAccess
- AmazonEC2ContainerRegistryFullAccess
- AmazonS3FullAccess
- CloudWatchFullAccess
- AWSCloudFormationFullAccess
- AWSBillingReadOnlyAccess
- AWSLambda_FullAccess

Note, these policies are broader than required for the deployment of Crunchbase. Giving more access than required does not follow the best practice for least-privelege, for more [information](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html).


### Installation
Check out [this repository](https://github.com/UtrechtUniversity/ia-webscraping), and make sure you checkout the 'main' branch. Open a terminal window and navigate to the `code` directory.
```bash
# Go to code folder
$ cd code
```

#### Configuring Lambda functions and Terraform
The `build.sh` script in this folder will for each of the Lambda functions:
- install all requirements from the 'requirements.txt' file in the function's folder
- create a zip file
- calculate a hash of this zipfile
- upload all relevant files to the appropriate S3 bucket

You can run `build.sh` with the following parameters to configure your scrape job:

- `-c <code bucket name>`: the name of the S3 bucket you've created for the code (see 'Prerequisites'). Use just the buckets name,
omitting the scheme (for example: 'my-code-bucket', *not* 's3://my-code-bucket').
- `-r <result bucket name>`: the name of the S3 bucket for your results. This will be created automatically. Again, specify just
the name (for example: 'my-result-bucket').
- `-l <lambda prefix>`: will be prefixed the Lambda functions' name. Useful for keeping different functions apart, if you
are running more Lambda's on the same account.
- `-a <AWS profile>`: the name of you local AWS profile (see 'Prerequisites'; for example: 'crunch').
- `-f <formats to save>`: the scraper can save all readable text from a html-page (for text analysis), as well as a list of
links present in each page (useful for network analysis). The default is text and links (`-f "txt,links"`). Saving
full html-pages has been disabled.
- `-s <start year>`: start year of the time window for which the scraper will retrieve stored pages. This value affects all domains.
It can be overridden with a specific value _per domain_ during the [URL upload process](#upload-urls-to-be-scraped). Same for `-e`.
- `-e <end year>`: end year.
- `-m`: switch for exact URL match. By default, the program will retrieve all available pages who's URL *starts with* the domain
or URL you provide. By using the `-m` switch, the program will only retrieve exact matches of the provided domain or URL. Note that
while matching, the presence of absence of a 'www'-subdomain prefix is ignored (so you can provide either).
- `-x <maximum number of scraped pages per provided URL; 0 for unlimited>`: maximum number of pages to retrieve for each provided
domain (or URL). If a domain's number of URLs exceeds this value, all the URLs are first sorted by their length (shortest first)
and subsequently truncated to `-x` URLs.
- `-n`: Switch to skip re-install of third party packages.
- `-h`: Show help.


#### Building Lambda functions and uploading to AWS
Save the file and close the text editor. Then run the build script with the correct parameters, for instance:
```bash
$ ./build.sh \
  -c my_code_bucket \
  -r my_result_bucket \
  -l my_lambda \
  -a crunch \
  -s 2020 \
  -e 2022 \
  -x 1000
```
The script creates relevant Terraform-files, checks whether the code-bucket exists, installs all required Python-packages,
zips the functions, and uploads them to the code bucket.

If you run the build-script repeatedly within a short time period (for instance when modifying the code), you
can execute subsequent builds with a tag to skip the re-installation of the Python dependencies and save time:
```
$ ./new_code_only.sh
```
This will repackage your code, and upload it to the appropriate bucket. The lambda will eventually pick up the new code
version; to make sure that the new code is used, go the appropriate function in the Lambda-section of the AWS console,
and in the section 'Source', click 'Upload from'. Choose 'Amazon S3 location', and enter the S3-path of the uploaded zip-file.
You can find the paths at the end of the output of the `new_code_only.sh` script (e.g. `s3://my_code_bucket/code/my_lambda-cdx.zip`)


#### Additional Terraform configuration (optional)
All relevant Terraform-settings are set by the build-script. There are, however, some defaults that can be changed.
These are in the file [terraform.tfvars](terraform/terraform.tfvars), below the line '--- Optional parameters ---':

```php
[...]

# ------------- Optional parameters -------------
# Uncomment if you would like to use these parameters.
# When nothing is specified, defaults apply.

# cdx_logging_level = [CDX_DEBUG_LEVEL; DEFAULT=error]

# scraper_logging_level = [SCRAPER_DEBUG_LEVEL; DEFAULT=error]

# sqs_fetch_limit = [MAX_MESSAGES_FETCH_QUEUE; DEFAULT=1000]

# sqs_cdx_max_messages = [MAX_CDX_MESSAGES_RECEIVED_PER_ITERATION; DEFAULT=10]

# cdx_lambda_n_iterations = [NUMBER_ITERATIONS_CDX_FUNCTION=2]

# cdx_run_id = [CDX_RUN_METRICS_IDENTIFIER; DEFAULT=1]
```

See the [variables file](/code/terraform/variables.tf) for more information on each of these variables.

Please note that [terraform.tfvars](terraform/terraform.tfvars) is automatically generated when you run the build-script,
overwriting any manual changes you may have made. If you wish to modify any of the variables in the file, do so _after_
you've successfully run `build.sh`.


#### Initializing Terraform
_init_

The `terraform init` command is used to initialize a working directory containing Terraform configuration files.
This is the first command that should be executed after writing a new Terraform configuration or cloning an
existing one from version control. This command needs to be run only once, but is safe to run multiple times.
```bash
# Go to terraform folder
$ cd terraform

# Initialize terraform
$ terraform init
```
Optionally, if you have made changes to the backend configuration:
```bash
$ terraform init -reconfigure
```
_plan_

The `terraform plan` command is used to create an execution plan. Terraform performs a refresh, unless explicitly
disabled, and then determines what actions are necessary to achieve the desired state specified in the configuration
files. The optional -out argument is used to save the generated plan to a file for later execution with
`terraform apply`.
```bash
$ terraform plan -out './plan'
```
_apply_

The `terraform apply` command is used to apply the changes required to reach the desired state of the configuration,
or the pre-determined set of actions generated by a terraform plan execution plan. By using the “plan” command before
“apply,” you’ll be aware of any unforeseen errors or unexpected resource creation/modification!
```bash
$ terraform apply "./plan"
```

For convenience, all the Terraform-steps can also be run from a single bash-file:
```bash
$ ./terraform.sh
```

## Running the pipeline

### Upload URLs to be scraped
Scraping is done in two steps:
1. After uploading a list of domains to be scraped to a queue, the 'CDX' Lambda-function queries the API of the [Internet
Archive](https://archive.org/web/) (IA) and retrieves all archived URLs for each domain. These include all available
different (historical) versions of each page for the specified time period. After filtering out irrelevant URLs (images,
JavaScript-files, stylesheets etc.), the remaining links are sent to a second queue for scraping.
2. The 'scrape' function reads links from the second queue, retrieves the corresponding pages from the Internet Archive,
and saves the contents to the result bucket. The contents are saved as Parquet datafiles.

The `fill_sqs_queue.py` script adds domains to be scraped to the initial queue (script is located in the [code folder](code/)):
```bash
# Fill sqs queue
$ python fill_sqs_queue.py [ARGUMENTS]
```
```
Arguments:
  --infile, -f       CSV-file with domains. The appropriate column should have 'Website' as
                     header. If you're using '--year-window' there should also be a column
                     'Year'.
  --job-tag, -t      Tag to label a batch of URLs to be scraped. This tag is repeated in all
                     log files and in the result bucket, and is intended to keep track of all
                     data and files of one run. Max. 32 characters.
  --queue, -q        name of the appropriate queue; the correct value has been set by 'build.sh'
                     (optional).
  --profile, -p      name of your local AWS profile; the correct value has been set by 'build.sh'
                     (optional).
  --author, -a       author of queued messages; the correct value has been set by 'build.sh'
                     (optional).
  --first-stage-only switch to use only the first step of the scraping process (optional, default
                     false). When used, the domains you queue are looked up in the IA, and the
                     resulting URLs are filtered and, if appropriate, capped, and logged, but not
                     passed on to the scrape-queue. 
  --year-window, -y  number of years to scrape from a domain's start year (optional). Requires
                     the presence of a column with start years in the infile.


Example:
$ python fill_sqs_queue.py -f example.csv -t "my first run (2022-07-11)" -y 5
```
For each domain, the script creates a message and loads it into the CDX-queue, after which processing automatically
starts.

### Monitor progress
Each AWS service in the workflow can be monitored in the AWS console. The CloudWatch logs provide additional information
on the Lambda functions. Set the logging level to 'info' to get verbose information on the progress.

#### CDX-queue
For each domain a message is created in the CDX-queue, which can be monitored through the
'Simple Queue Service' in the AWS Console. The CDX-queue is called `my-lambda-cdx-queue` (`my-lambda` being the value
of `LAMBDA_NAME` you configured; see 'Configuring Lambda functions and Terraform'). The column 'Messages available'
displays the number of remaining messages in the queue, while 'Messages in flights' shows the number of messages
currently being processed. Please note that this process can be relatively slow; if you uploaded thousands of links,
expect the entire process to take several hours or longer.

#### Scrape-queue
The scrape-queue (`my-lambda-scrape-queue`) contains a message for each URL to be scraped. Depending on the size of the
corresponding website, this can be anything between a few and thousands of links per domain (and occasionally none).
Therefore, the number of messages to be processed from the scrape-queue is usually many times larger than the number
loaded into the CDX-queue. The is further increased by the availability of multiple versions of the same page.  

#### Stopping a run
If you need to stop a run, first go to the details of the CDX-queue (by clicking its name), and choose 'purge'. This
will delete all messages from the queue that are not in flight yet. Then do the same for the scrape-queue.


#### CloudWatch (logfiles)
While running, both functions log metrics to their own log group. These can be accessed through the CloudWatch module 
of the AWS Console.

Each function logs to its own log group, `/aws/lambda/my_lambda-cdx` and `/aws/lambda/my_lambda-scrape`. These logs
contain mostly technical feedback, and are useful for debugging errors.
Besides standard process info, the lambda's write project specific log lines to their respective log streams. These
can be identified by their labels.

_CDX metrics_  (Label: **[CDX_METRIC]**)

Metrics per domain
+ job tag
+ domain
+ start year of the retrieval window
+ end year of the retrieval window
+ number of URLs retrieved from the IA
+ number that remains after filtering out filetypes that carry no content (such as JS-files, and style sheets)
+ number sent to the scrape-queue, after filtering and possible capping.
The last two numbers are usually the same, unless you have specified a maximum number of scraped pages per provided domain, and a domain
has more pages than that maximum.

_Scrape metrics_  (Label **[SCRAPE_METRIC]**)

Metrics per scraped URL
+ job tag
+ domain for which the CDX-function retrieved the URL.
+ full URL that was scraped.
+ size saved txt (in bytes)
+ size saved links (in bytes)

#### Browsing, querying and downloading log lines
All log lines can be browsed through the Log Groups of the CloudWatch section of the AWS Console, and, up to a point, queried via the 
Log Insights function. To download them locally, install and run [saw](https://github.com/TylerBrock/saw). A typical command would be:

```bash
$ saw get /aws/lambda/my_lambda-cdx --start 2022-06-01 --stop 2022-06-05 | grep CDX_METRIC
```
This tells `saw` to get all log lines from the `/aws/lambda/my_lambda-cdx` stream for the period `2022-06-01 <= date < 2022-06-05`.
The output is passed on to `grep` to filter out only lines containing 'CDX_METRIC'


## Results
All scraped content is written to the S3 result bucket (the name of which you specified in the `RESULT_BUCKET` variable) as
Parquet-files, a type of data file ([Apache Parquet docs](https://parquet.apache.org/docs/)). The files are written by
Kinesis Firehose, which controls when results are written, and to which file. Firehose flushes records to file, and rolls
over to a new Parquet-file, whenever it is deemed necessary, This make the number of Parquet-files, as well as the number
of records within each file somewhat unpredictable (see below for downloading and processing of Parquet-files,
including compiling them in less and larger files). The files are ordered in subfolders representing the year, month and day
they were created. For instance, a pipeline started on December 7th 2022 will generate a series of Parquet-files such as:

```bash
s3://my_result_bucket/2022/12/07/scrape-kinesis-firehose-9-2022-12-07-09-23-43-00efb47c-021f-475f-a119-1aecf2b15ed9.parquet
```

### Processing Parquet-files

#### Downloading Parquet files from S3
Download the generated Parquet-files from the appropriate S3 bucket using the `sync_s3.sh` bash file in the 
[scripts-folder](code/scripts/). The script's first parameter is the address of the appropriate bucket and,
optionally, the path within it. The second parameter is path of the local folder to sync to.

The script uses the `sync` command of the AWS-client, which mirrors the remote contents to a
local folder. This means that if run repeatedly, only new files will be downloaded each time.
The command works recursively so subfolder structure is maintained.

The example command below syncs all the files and subfolders in the folder `/2022/12/` in the
bucket `my-result-bucket` to the local folder `/my_data/parquet_files/202211/`.

```bash
$ sync_s3.sh s3://my-result-bucket/2022/12/ /my_data/parquet_files/202211/
```

Be aware that there will be some time between completion of the final invocation of the
scraping lambda, and the writing of its data by the Kinesis Firehose (usually no more than
15 minutes).

#### Quick check of downloaded files
To make sure all files were downloaded, check the number of files you just downloaded with the
number in the S3 bucket. The latter can be calculated by accessing the AWS Console. Navigate
towards the S3-module, and then the appropriate S3 bucket, and select the appropriate folders.
Next, click the 'Actions'-button and select 'Calculate total size'; this will give you the
total number of objects and their collective size.

#### Split files based on job_tag
If the Parquet-files contain data of multiple runs with different job tags, they can be split
accordingly. Run the following command to recursively process all Parquet-files in the folder
`/my_data/parquet_files/202211/` and write them to `/my_data/parquet_files/jobs/`.

```bash
$ python parquet_file_split.py \
    --input '/my_data/parquet_files/202211/' \
    --outdir '/my_data/parquet_files/jobs/' 
```
This will result in a subfolder per job tag in the output folder. Within each subfolder, there
will be a series of Parquet-files containing only the records for that job tag.

#### Combining split files into larger files
Optionally, to combine many small Parquet-files into larger files, run the following command:

```bash
$ python parquet_file_join.py \
    --indir '/my_data/parquet_files/jobs/my_job/' \
    --outdir '/my_data/parquet_files/jobs/my_job_larger/' \
    --basename 'my_job' \
    --max-file-size 100 \
    --delete-originals 
```
+ `basename`: the basename of the new, larger files. Incremental numbers and '.parquet'
extensions are added automatically.
+ `max-file-size`: optional parameter to set the appromximate maximum file size in MB of the resulting files (default: 25)
+ `delete-originals`: optional, default False.

#### Reading Parquet files
If you are using Python, you can read the Parquet files into a Pandas or Polars DataFrame, 
or use the [pyarrow](https://pypi.org/project/pyarrow/) package.
For R you can use the [arrow](https://arrow.apache.org/docs/r/reference/read_parquet.html) package.

Each Parquet-file contains a number of rows, each one corresponding with one scraped URL, with the following columns:
+ job_tag: id.
+ domain: domain for which the CDX-function retrieved the URL.
+ url: full URL that was scraped.
+ page_text: full page text
+ page_links: list of page links
+ timestamp: timestamp of creation of the record


## Cleaning up
### Deleting the infrastructure
After finishing scraping, run the following [command](https://www.terraform.io/docs/commands/destroy.html), to
clean up the AWS resources that were deployed by Terraform:
```bash
# Go to terraform folder
$ cd terraform

# Clean up AWS resources
$ terraform destroy
```

This leaves in tact the code and result buckets.

### Deleting buckets
You can delete s3 buckets through the AWS management interface. When there
are a lot of files in a bucket, the removal process in the management interface sometimes hangs before it finishes.
In that case it is advisable to use the AWS client. Example command:
```bash
$ aws s3 rb s3://my_result_bucket --force
```
This will delete all files from the bucket, and subsequently the bucket itself.

## About the Project

### Architecture
The ia-webpository utilizes the following AWS services:
- **Simple Queueing System**: manage distribution of tasks among Lambda functions and give insight in results
    - queue with initial urls
    - queue with scraping tasks
- **AWS Lambda**: run code without the need for provisioning or managing servers
    - lambda to retrieve cdx records for initial urls, filter these and send tasks to scraping queue
    - lambda to retrieve webpages for cdx records and send these to s3 bucket
- **S3**: for storage of the HTML pages
- **CloudWatch**: monitor and manage AWS services
   - CloudWatch to monitor the metrics of the SQS queue and Lambda functions
   - CloudWatch to trigger the Lambda function on a timely basis, the interval can be changed to throttle the process
- **Kinesis Data Firehose**: delivery streams
   - data from the scraping lambda is pushed to S3 using the Kinesis Data Firehose delviery system.
   - stores data in Apache Parquet files.

Configuration of the necessary AWS infrastructure and deployment of the Lambda functions is done using the
“infrastructure as code” tool Terraform.

Deploying this solution will result in the following scrape pipeline in the AWS Cloud.

![Alt text](docs/architecture_overview.png?raw=true "Architecture Overview")

(n.b. schema lacks Kinesis Data Firehose component)

### Built with

- [Terraform](https://www.terraform.io/)
- [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [asyncio](https://docs.aiohttp.org/en/stable/glossary.html#term-asyncio)

### License and citation

The code in this project is released under [MIT](LICENSE).

Please cite this repository as 

Schermer, M., Bood, R.J., Kaandorp, C., & de Vos, M.G. (2023). "Ia-webscraping: An AWS workflow for collecting webpages from the Internet Archive "  (Version 1.0.0) [Computer software]. https://doi.org/10.5281/zenodo.7554441

[![DOI](https://zenodo.org/badge/329035317.svg)](https://zenodo.org/badge/latestdoi/329035317)


### Team

**Researcher**:

- Jip Leendertse (j.leendertse@uu.nl)

**Research Software Engineer**:

- Casper Kaandorp (c.s.kaandorp@uu.nl)
- Martine de Vos (m.g.devos@uu.nl)
- Robert Jan Bood (robert-jan.bood@surf.nl)
- Maarten Schermer (m.d.schermer@uu.nl)

This project is part of the Public Cloud call of [SURF](https://www.surf.nl/en/)

