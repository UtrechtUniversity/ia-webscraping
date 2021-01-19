package main

import (
	"bufio"
	"context"
	"errors"
	"fmt"
	"io"
	"io/ioutil"
	"log"
	"net/http"
	"os"
	"strings"
	"sync"
	"sync/atomic"
	"time"
)

const (
	lambdaURL              = "https://bk0g3z2x09.execute-api.us-east-1.amazonaws.com/dev?url=%s" // Lambda url that serves as a proxy
	internetArchiveCDXUrl  = "http://web.archive.org/cdx/search/cdx?url=%s"                      // IA cdx endpoint that returns all pages in the Internet Archive for a specific url
	internetArchivePageUrl = "https://web.archive.org/web/%s/%s"                                 // IA endpoint used to retrieve a single archived page. Parameters for each page can be found by using the IA's cdx endpoint
	goroutineCount         = 4                                                                   // Number of goroutines to start to fetch pages concurrently. Values above 1000 probably have no effect since since AWS caps the number of concurrent lambda calls

	timeout        = time.Second * 20
	retriesPerPage = 2         // Max number of times to retry getting a page on error
	scrapeFolder   = "scraped" // Folder to save scraped pages to
)

// Urls to fetch.
var orgs = []string{
	"2ie-edu.org",
	"aaaid.org",
	//"aacb.org",
	//"aalco.int",
	//"aardo.org",
	//"abn.ne",
	//"acp.int",
	//"acs-aec.org",
	//"acwl.ch",
	//"adb.org",
	//"afdb.org",
	//"aflsf.org",
	//"afreximbank.com",
	//"africa-re.com",
	//"africanguaranteefund.com",
	//"africarice.org",
	//"afristat.org",
	//"agfund.org",
	//"aibd.org.my",
	//"aihja.org",
	//"aitic.org",
	//"aladi.org",
	//"alolabor.org",
	//"amcow-online.org",
	//"amf.org.ae",
	//"anrpc.org",
	//"aoad.org",
	//"apccsec.org",
	//"apec.org",
	//"apo-tokyo.org",
	//"appu-bureau.org",
	//"apt.int",
	//"arabfund.org",
	//"arctic-council.org",
	//"aripo.org",
	//"asbasupervision.com",
	//"asean.org",
	//"asecnaonline.asecna.aero",
	//"asef.org",
	//"asianclearingunion.org",
	//"asianrecorp.com",
	//"au.int",
	//"auf.org",
	//"avrdc.org",
}

// Retrieves all pages archived in the Internet Archive for the urls in the orgs slice and saves them to disk
// Uses the lambda-scape-single-page lambda as a proxy. Starts goroutineCount goroutines to fetch pages concurrently.
func main() {
	const (
		jobChannelSize = goroutineCount * 2 // Job channel that is used to pass jobs to all goroutines. Buffered to make sure each goroutines don't have to wait for a new job
	)

	var (
		pageCount  int64 // Number of urls fetched
		bytesCount int64 // Number of bytes fetched

		wg sync.WaitGroup // Waitgroup that is used wait until all workers are done
	)

	if _, err := os.Stat(scrapeFolder); os.IsNotExist(err) {
		if err := os.Mkdir(scrapeFolder, 0755); err != nil {
			log.Fatal(err)
		}
	}

	start := time.Now()                       // Start time
	urls := make(chan string, jobChannelSize) // Channel that acts as a queue to distribute jobs to all workers/goroutines

	// Spawn goroutines that each act as workers that keep fetching jobs from the urls channel that acts as a queue
	for n := 0; n < goroutineCount; n++ {
		wg.Add(1) // Increase the waitgroup counter

		// Start a worker in a separate goroutine that keeps taking urls from the queue and fetches them until the urls
		// channel closes. The worker will then exit
		go func(urls chan string) {
			defer wg.Done() // Decrease the waitgroup counter

			// Keep fetching urls from the urls channel until the channel is closed
			for url := range urls {
				var pageHTML []byte
				for i := 0; i < retriesPerPage; i++ {
					var err error
					pageHTML, err = fetch(fmt.Sprintf(lambdaURL, url))
					if err != nil {
						log.Printf("error fetching %s: %s", url, err)
						continue
					}
					break // No error
				}

				// Write the html to disk
				if err := ioutil.WriteFile(fmt.Sprintf("%s/%d.html", scrapeFolder, atomic.LoadInt64(&pageCount)), pageHTML, 0644); err != nil {
					log.Fatal("error writing file", err)
				}

				// Increase file count
				atomic.AddInt64(&pageCount, 1) // Add to the total count using the atomic package to avoid a data race

				// Increase byte count
				atomic.AddInt64(&bytesCount, int64(len(pageHTML)))
			}
		}(urls)
	}

	// Counter that shows progress
	go func() {
		for {
			fmt.Printf("\rDownloaded %d pages", atomic.LoadInt64(&pageCount))
			time.Sleep(time.Millisecond * 200)
		}
	}()

	// Go through each org and use the IA cdx endpoint to get all pages that are archived for this org.
	// Don't use the default Go http client since it doesn't set a timeout by default. Although rare, this can lead to hangs
	// with misbehaving http servers.
	// The http client is reused to take advantage of http2's connection reuse
	httpClient := &http.Client{Timeout: timeout, Transport: http.DefaultTransport}

	// Go through each organisation url in the orgs slice
	for _, org := range orgs {
		//Create a new context with a timeout
		ctx, cancel := context.WithTimeout(context.Background(), timeout)

		// Fetch all lines in the cdx file
		lines, err := fetchLines(ctx, httpClient, fmt.Sprintf(lambdaURL, fmt.Sprintf(internetArchiveCDXUrl, org)))
		if err != nil {
			cancel()
			log.Printf("error getting %s: %s\n", org, err)
			continue
		}

		var urlsDone = map[string]struct{}{} // Used to skip pages with the same digest

		// Go through each line in the cdx file
		for i := range lines {
			// For each line extract the timestamp, page url and digest
			timestamp, url, digest, err := extractFieldsFromLine(lines[i])
			if err != nil {
				log.Println("error extracting field from line:", err)
				continue // Just continue on error
			}

			if _, ok := urlsDone[digest]; ok {
				continue // Skip pages with the exact same content
			}

			// Create the IA url for this page and add it to the jobs queue
			urls <- fmt.Sprintf(internetArchivePageUrl, timestamp, url)

			// Mark page as done
			urlsDone[digest] = struct{}{}
		}
	}

	// Close the urls channel. As a result the channel will be emptied and the workers will exit
	close(urls)

	// Wait until all goroutines are finished
	wg.Wait()

	log.Printf("\rDone. Fetched %d pages for %d organizations. Took %s and %d bytes. Average time per page: %s at %d bytes/s", pageCount, len(orgs), time.Since(start), bytesCount, time.Since(start)/time.Duration(pageCount), bytesCount/int64(time.Since(start).Seconds()))
}

// extractFieldsFromLine returns the timestamp, url and digest of a single page from a line in a cdx file
func extractFieldsFromLine(line string) (string, string, string, error) {
	fields := strings.Split(line, " ")
	if len(fields) != 7 {
		return "", "", "", errors.New("invalid field count")
	}

	timestamp := fields[1]
	url := fields[2]
	digest := fields[5]

	return timestamp, url, digest, nil
}

// Fetch requests an url and returns its response body
func fetch(url string) ([]byte, error) {
	// Don't use the default Go http client since it doesn't set a timeout by default. Although rare, this can lead to hangs
	// with misbehaving http servers.
	httpClient := &http.Client{Timeout: timeout, Transport: http.DefaultTransport}

	// Create a context with timeout
	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()

	// Create a new request using the passed context
	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, err
	}

	// Do the request
	resp, err := httpClient.Do(req)
	if resp != nil {
		defer resp.Body.Close() // On exit close the response body
	}
	if err != nil {
		return nil, err
	}

	// Check the response code
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return nil, fmt.Errorf("fetch returned non 2xx status code: %d: %s", resp.StatusCode, http.StatusText(resp.StatusCode))
	}

	// Read the whole response body
	data, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	return data, nil
}

// Fetch requests an url and returns all lines in the response
func fetchLines(ctx context.Context, httpClient *http.Client, url string) ([]string, error) {
	// Create a new request using the passed context
	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, err
	}

	// Do the request
	resp, err := httpClient.Do(req)
	if resp != nil {
		defer resp.Body.Close() // On exit close the response body
	}
	if err != nil {
		return nil, err
	}

	// Check the response code
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return nil, fmt.Errorf("fetch returned non 2xx status code: %d: %s", resp.StatusCode, http.StatusText(resp.StatusCode))
	}

	var lines []string

	scanner := bufio.NewScanner(resp.Body) // A buffered scanner that reads lines from a reader

	// Keep reading until no more are left
	for scanner.Scan() {
		// Append the text of the line to the result
		lines = append(lines, scanner.Text())
	}

	// Check the scanner for errors
	if err := scanner.Err(); err != nil {
		return nil, err
	}

	// Make sure the whole body is read to ensure connection can be reused
	_, _ = io.Copy(ioutil.Discard, resp.Body)

	return lines, nil
}
