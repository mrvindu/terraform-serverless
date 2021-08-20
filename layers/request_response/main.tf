terraform {
  backend "s3" {
    encrypt        = true
    bucket         = "akp-new-terraform-remote-state-storage-s3"
    dynamodb_table = "terraform-state-lock-dynamo"
    region         = "us-east-2"
    key            = "lambda/src/layers/request_response/terraform.state"
  }
}

data "archive_file" "request-response-layer-zip" {
  type        = "zip"
  source_dir  = "${path.module}/lamda/"
  output_path = "request_response_layer.zip"
}

resource "aws_lambda_layer_version" "request-response-layer" {
  filename         = "request_response_layer.zip"
  layer_name       = "request_response_layer"
  source_code_hash = filebase64sha256("request_response_layer.zip")

  compatible_runtimes = ["python3.7"]
}
