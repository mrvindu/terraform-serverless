#!/usr/bin/env bash

version=$(aws lambda list-versions-by-function --function-name "${PWD##*/}" --query "Versions[-1]" | jq -r '.Version')
sed -i '' "s/function_version = \"[[:digit:]]*\"/function_version = \"$version\"/g" main.tf && terraform apply -auto-approve
