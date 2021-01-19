package main

import (
	"context"
	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-lambda-go/lambda"
	"io/ioutil"
	"net/http"
)

// This lambda function returns the current IP of the running lambda
func main() {
	lambda.Start(handleRequest)
}

// Handle the request
func handleRequest(_ context.Context, _ events.APIGatewayProxyRequest) (events.APIGatewayProxyResponse, error) {
	// Get the external ip of the running lambda by calling ipify.org. There is currently no other way to determine the
	// external ip address of a running lambda function
	res, err := http.Get("https://api.ipify.org")
	if res != nil {
		defer res.Body.Close() // Close the response body when done
	}
	if err != nil {
		return events.APIGatewayProxyResponse{}, err
	}

	// Read the whole response body
	ip, err := ioutil.ReadAll(res.Body)
	if err != nil {
		return events.APIGatewayProxyResponse{}, err
	}

	// Return the ip from the response body to the caller
	return events.APIGatewayProxyResponse{Body: string(ip), StatusCode: http.StatusOK}, nil
}
