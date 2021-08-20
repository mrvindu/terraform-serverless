terraform {
  backend "s3" {
    encrypt        = true
    bucket         = "akp-new-terraform-remote-state-storage-s3"
    dynamodb_table = "terraform-state-lock-dynamo"
    region         = "us-east-2"
    key            = "apigateway/list_users/terraform.state"
  }
}

data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

locals {
  stages = ["dev", "prod"]
}

resource "aws_lambda_permission" "allow_api_gateway_dev" {
  count = length(local.stages)

  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_name
  qualifier     = local.stages[count.index]
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.api.execution_arn}/${local.stages[count.index]}/*"
}

resource "aws_api_gateway_rest_api" "api" {
  name        = "list_users"
  description = "API for listing users given some filters"
}

data "aws_cognito_user_pools" "main-user-pool" {
  name = "akp-users"
}

locals {
  http_methods = ["POST"]
}

resource "aws_api_gateway_method" "method" {
  count = length(local.http_methods)

  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_rest_api.api.root_resource_id
  http_method   = local.http_methods[count.index]
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "integration" {
  count = length(local.http_methods)

  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_rest_api.api.root_resource_id
  http_method             = aws_api_gateway_method.method.*.http_method[count.index]
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = "arn:aws:apigateway:${data.aws_region.current.name}:lambda:path/2015-03-31/functions/arn:aws:lambda:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:function:list_users:$${stageVariables.lambdaAlias}/invocations"
}

resource "aws_api_gateway_method_response" "response-200" {
  count = length(local.http_methods)

  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_rest_api.api.root_resource_id
  http_method = aws_api_gateway_method.method.*.http_method[count.index]
  status_code = "200"
}

resource "aws_api_gateway_integration_response" "list_users-integration-response" {
  count = length(local.http_methods)

  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_rest_api.api.root_resource_id
  http_method = aws_api_gateway_method_response.response-200.*.http_method[count.index]
  status_code = "200"
}

resource "aws_api_gateway_deployment" "deployment" {
  depends_on = [aws_api_gateway_integration.integration]
  count      = length(local.stages)

  rest_api_id       = aws_api_gateway_rest_api.api.id
  stage_name        = "temp-${local.stages[count.index]}"
  description       = "${local.stages[count.index]} deployment"
  stage_description = "${local.stages[count.index]} stage"
}

resource "aws_api_gateway_stage" "stage" {
  count = length(local.stages)

  deployment_id = aws_api_gateway_deployment.deployment.*.id[count.index]
  rest_api_id   = aws_api_gateway_rest_api.api.id
  stage_name    = local.stages[count.index]

  variables = {
    lambdaAlias = local.stages[count.index]
  }
}

resource "aws_api_gateway_documentation_part" "request-body-post" {
  location {
    type   = "REQUEST_BODY"
    method = "POST"
    path   = "/"
  }

  properties  = "{\"filter\": \"email = \\\"omar.el.said89@gmail.com\\\"\"}"
  rest_api_id = aws_api_gateway_rest_api.api.id
}

resource "aws_api_gateway_documentation_part" "api" {
  location {
    type = "API"
  }

  properties  = "{\"description\": \"This is for example\"}"
  rest_api_id = aws_api_gateway_rest_api.api.id
}

