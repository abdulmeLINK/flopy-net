#!/bin/sh
# Simple health check script for the landing page container

curl -s -o /dev/null -w "%{http_code}" http://localhost:80

# Returns the HTTP status code (200 if healthy)
