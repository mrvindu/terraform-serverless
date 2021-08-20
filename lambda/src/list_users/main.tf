terraform {
  backend "s3" {
    encrypt        = true
    bucket         = "akp-new-terraform-remote-state-storage-s3"
    dynamodb_table = "terraform-state-lock-dynamo"
    region         = "us-east-2"
    key            = "lambda/deployment/list_users/terraform.state"
  }
}

module "global_variables" {
  source = "../../../global_variables"
}


data "aws_region" "current" {}
data "aws_caller_identity" "current" {}
data "archive_file" "zip" {
  type        = "zip"
  source_dir  = "${path.module}/lamda/"
  output_path = "lambda.zip"
}

resource "aws_lambda_function" "lambda" {
  filename         = "lambda.zip"
  source_code_hash = data.archive_file.zip.output_base64sha256
  description      = "Lambda used by API to list users given some filters"
  function_name    = "list_users"
  handler          = "list_users.handler"
  role             = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/LambdaListUsersRole"
  runtime          = "python3.7"
  publish          = true
  timeout          = 10

  layers = [
    "arn:aws:lambda:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:layer:request_response_layer:${module.global_variables.request_response_lv}",
    "arn:aws:lambda:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:layer:db_layer:${module.global_variables.db_lv}",
    "arn:aws:lambda:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:layer:cognito_layer:${module.global_variables.cognito_lv}",
  ]
}

resource "aws_lambda_alias" "dev-alias" {
  name             = "dev"
  function_version = "$LATEST"
  description      = "Lambda alias to be used by client to point to dev version of lambda"
  function_name    = aws_lambda_function.lambda.arn
}

resource "aws_lambda_alias" "prod-alias" {
  name             = "prod"
  function_version = "18"
  description      = "Lambda alias to be used by client to point to production version of lambda"
  function_name    = aws_lambda_function.lambda.arn
}
