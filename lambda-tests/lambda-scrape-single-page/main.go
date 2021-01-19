package main

import (
	"context"
	"fmt"
	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-lambda-go/lambda"
	"io/ioutil"
	"net/http"
	"time"
)

const (
	timeout = time.Second * 15 // Timeout for the fetch
)

// This lambda function returns the html of the url that was set in the url param
// Example: https://xxxxx.execute-api.us-east-1.amazonaws.com/dev?url=https://google.com
// The page to scrape can be set using the GET parameter "url"
func main() {
	lambda.Start(handleRequest)
}

// Handle request
func handleRequest(ctx context.Context, request events.APIGatewayProxyRequest) (events.APIGatewayProxyResponse, error) {
	// Get the url parameter from the request
	url := request.QueryStringParameters["url"]

	// Check if the url parameter is set
	if url == "" {
		return events.APIGatewayProxyResponse{Body: "url get parameter is required", StatusCode: http.StatusBadRequest}, nil
	}

	// Fetch the remote html page
	body, err := fetch(ctx, url)
	if err != nil {
		// Request returned an error. Return the error that was received from the fetch() and a 502 status
		return events.APIGatewayProxyResponse{Body: err.Error(), StatusCode: http.StatusBadGateway}, nil
	}

	// Return the retrieved html. Since lambda returns a content-type: application/json by default, when requesting this
	// lambda in a browser the retrieved html is not interpreted but printed instead.
	return events.APIGatewayProxyResponse{Body: string(body), StatusCode: http.StatusOK}, nil
}

// Fetch requests an url and returns its response body
func fetch(ctx context.Context, url string) ([]byte, error) {
	// Don't use the default Go http client since it doesn't set a timeout by default. Although rare, this can lead to hangs
	// with misbehaving http servers.
	httpClient := &http.Client{Timeout: timeout, Transport: http.DefaultTransport}

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
