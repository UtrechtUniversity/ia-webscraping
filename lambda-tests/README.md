# Tests

Simple test to determine the viability of using AWS's lambda's for web scraping. Once deployed to AWS, the lambda functions 
in these packages are triggered by calling them over http as if they are an API endpoint. Parameters are passed as GETs.

Included:
* `return-ip` lambda that only returns the external IP of the machine it is running on
* `scrape-single-page` lambda that fetches and returns a single html page to the caller. The url to be fetched can be set by passing the `url` parameter
* `scrape-controller` can be run on a local machine to fetch urls in bulk using a deployed `scrape-single-page` lambda as a proxy 

### Requirements:
* Go (see https://golang.org/doc/install)
* AWS account
* Serverless framework (see https://www.serverless.com/framework/docs/getting-started/) 

### Deployment:

To deploy a lambda it must first be build:
```
cd lambda-scrape-single-page
go build
GOOS=linux GOARCH=amd64 go build -a -installsuffix cgo -ldflags="-w -s" -o bin/crunchbase-test-return-ip .
```
(note: the env vars included with the go build command are needed to ensure the executable is compiled for linux amd 64 bit and are only needed
when cross-compiling. The other flags are used to minimize the build size by excluding debug symbols and the like from the final build, and are optional.)

Deploy using Serverless to AWS. Serverless will take care of all needed configuration and deployment of needed infrastructure 
like an API Gateway. On success Serverless will display a URL at which the newly created Lambda endpoint can be triggered.
```
serverless deploy
```

### Run Tests:

The scrape controller package can be run locally to scrape pages in bulk. To use it first deploy the `scrape-single-page` 
lambda that acts as a proxy that fetches pages for you. In `scrape-controler/main.go` set `lambdaUrl` to the URL that Serverless returned. The controller fetches urls from the Internet Archive cdx endpoint. 
The pages in these cdx files are then fetched in parallel without any rate limiting.

### Results:
These tests were run on a MacBook Pro over WiFi. Each run uses a different number of concurrent workers to fetch urls as 
fast as possible. Five different organizations were used in each run to avoid any short-lived cache the IA might have. No 
rate limiting was encountered during any of these tests.

#### Concurrent workers: 4
`Fetched 4068 pages for 5 organizations. Took 44m41.442522346s and 303429053 bytes. Average time per page: 659.154995ms at 113177 bytes/s`

#### Concurrent workers: 8
`Fetched 815 pages for 5 organizations. Took 4m4.546390958s and 55941304 bytes. Average time per page: 300.056921ms at 229267 bytes/s`

#### Concurrent workers: 16
`Fetched 1728 pages for 5 organizations. Took 4m10.721084038s and 219235867 bytes. Average time per page: 145.09322ms at 876943 bytes/s`

#### Concurrent workers: 32
`Fetched 418 pages for 5 organizations. Took 44.877017781s and 24914167 bytes. Average time per page: 107.361287ms at 566231 bytes/s`

#### Concurrent workers: 64
`Fetched 1932 pages for 5 organizations. Took 1m26.057344289s and 194307659 bytes. Average time per page: 44.543139ms at 2259391 bytes/s`

#### Concurrent workers: 128
`Fetched 1511 pages for 5 organizations. Took 41.162798059s and 101084110 bytes. Average time per page: 27.24209ms at 2465466 bytes/s`

#### Concurrent workers: 256
`Fetched 1805 pages for 5 organizations. Took 30.216118783s and 180235691 bytes. Average time per page: 16.740232ms at 6007856 bytes/s`

#### Concurrent workers: 512
`Fetched 4602 pages for 6 organizations. Took 44.212297643s and 346703003 bytes. Average time per page: 9.607192ms at 7879613 bytes/s`

#### Concurrent workers: 1024
`Fetched 2809 pages for 8 organizations. Took 31.899931675s and 257402505 bytes. Average time per page: 11.35633ms at 8303306 bytes/s
`
