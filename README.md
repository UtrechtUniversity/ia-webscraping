# ia-webscraping

## Architecture
The ia-webscraping repository utilizes the following AWS services:
- SQS: to create a queue of scraping tasks, manage the distribution of these tasks among the fetching Lambda functions and give insight in the result of the task.
- AWS Lambda: to run the fetching code without the need for provisioning or managing servers.
- S3: for storage of the HTML pages
- CloudWatch: to monitor the metrics of the SQS queue and Lambda functions
- CloudWatch trigger: to trigger the Lambda function on a timely basis, the interval can be changed to throttle the process

Deploying this solution will result in the following scrape pipeline in the AWS Cloud.

```mermaid
flowchart TB


  subgraph Internet["The Internet"]
    InternetArchive[(InternetArchive)]
  end

  subgraph ResearcherUU["Researcher (UU)"]
    FillSQSQueue[/FillSQSQueue.py\]
  end

  subgraph Lambda_Fetch["Concurrent Fetch Lambda's"]
    LambdaFetch_1
    LambdaFetch_2
    LambdaFetch_N
  end

  subgraph AWS["AWS Cloud"]
    SQS_CDX
    Lambda_CDX
    Cloudwatch_Trigger
    SQS_Fetch
    Lambda_Fetch
    S3[(AWS S3)]
  end

  style AWS fill:#eef
  style Lambda_Fetch fill:#f96

  FillSQSQueue -- Fill SQS --> SQS_CDX
  Lambda_CDX -- Get URL --> SQS_CDX
  Lambda_CDX -- CDX API --> InternetArchive  
  Cloudwatch_Trigger -- Trigger Lambda --> Lambda_CDX
  Lambda_CDX  -- Create Fetch Tasks -->  SQS_Fetch
  SQS_Fetch -- Get Fetch Tasks --> Lambda_Fetch
  Lambda_Fetch -- Get HTML Page --> InternetArchive
  Lambda_Fetch -- Store HTML page --> S3

  click InternetArchive callback "https://archive.org/"
```

