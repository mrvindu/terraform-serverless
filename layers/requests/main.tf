terraform {
  backend "s3" {
    encrypt        = true
    bucket         = "akp-new-terraform-remote-state-storage-s3"
    dynamodb_table = "terraform-state-lock-dynamo"
    region         = "us-east-2"
    key            = "lambda/src/layers/requests/terraform.state"
  }
}

data "archive_file" "requests-layer-zip" {
  type        = "zip"
  source_dir  = "${path.module}/lamda/"
  output_path = "requests_layer.zip"
}

resource "aws_lambda_layer_version" "requests-layer" {
  filename         = "requests_layer.zip"
  layer_name       = "requests_layer"
  source_code_hash = filebase64sha256("requests_layer.zip")

  compatible_runtimes = ["python3.7"]
}
