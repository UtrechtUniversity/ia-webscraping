import boto3
from datetime import datetime, timedelta
import time

'''
    This script creates a cloudwatch query to retrieve the metric log statements of the CDX lambda function.
    The results of this query are collected and written to a csv file, containing: domain, run id, number of urls, number of filtered urls.
'''

client = boto3.client('logs')

CDX_RUN_ID = "2"
LAMBDA_FUNCTION_NAME = 'hello-world-python'
YEAR = 2021
MONTH = 3
DAY= 24

def main():
    print('Start Cloudwatch query for cdx scrape logs')
    #Define search query
    query = "fields @run, @domain | filter @message like \"[Metrics] run:" + str(CDX_RUN_ID) + "\" | parse @message /^.*run\:(?<@run>\d*)\sdomain:(?<@domain>.{1,})\sn_urls:(?<@n_urls>\d*)\sn_filtered_urls:(?<@n_furls>\d*)$/"

    # Define log group
    log_group = f'/aws/lambda/{LAMBDA_FUNCTION_NAME}'

    # Start query
    starttime = datetime.today().replace(year=YEAR,month=MONTH,day=DAY,hour=0, minute=0, second=0, microsecond=0).timestamp()
    endtime = datetime.today().replace(year=YEAR,month=MONTH,day=DAY,hour=23, minute=59, second=59, microsecond=999).timestamp()
    start_query_response = client.start_query(
        logGroupName=log_group,
        startTime=int(starttime),
        endTime=int(endtime),
        queryString=query,
    )

    # Start polling for results
    query_id = start_query_response['queryId']
    response = None
    while response == None or response['status'] == 'Running':
        print('Waiting for query to complete ...')
        time.sleep(1)
        response = client.get_query_results(
            queryId=query_id
        )
    # Log number of results
    print('number of companies: ' + str(len(response['results'])))
    # print(response['results'])

    #Write output to CSV file
    if len(response['results']) > 0:
        out_filename = f'./metrics_{YEAR}_{MONTH}_{DAY}.csv'
        print(f"write output to: '{out_filename}'")
        with open(out_filename, 'w') as out_file:
            out_file.write(f"domain,run,n_urls,n_furls\n")
            for comp in response['results']:
                domain = next(item for item in comp if item["field"] == "@domain")['value']
                n_urls = next(item for item in comp if item["field"] == "@n_urls")['value']
                n_furls = next(item for item in comp if item["field"] == "@n_furls")['value']
                run = next(item for item in comp if item["field"] == "@run")['value']
                out_file.write(f"{domain},{run},{n_urls},{n_furls}\n")

if __name__ == "__main__":
    main()
