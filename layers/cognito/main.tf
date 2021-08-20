terraform {
  backend "s3" {
    encrypt        = true
    bucket         = "akp-new-terraform-remote-state-storage-s3"
    dynamodb_table = "terraform-state-lock-dynamo"
    region         = "us-east-2"
    key            = "lambda/src/layers/cognito/terraform_common_layer_v17.tfstate"
  }
}
#layer 16 have dev Cognito user pool ID

resource "aws_s3_bucket_object" "lambda_layer" {
  bucket = "akplayerversions"
  key = "lambda/layers/cognito_layer/cognito_layer_17_${data.archive_file.cognito-layer-zip.output_base64sha256}.zip"
  source = data.archive_file.cognito-layer-zip.output_path
  depends_on = [
    data.archive_file.cognito-layer-zip,
  ]
}

data "archive_file" "cognito-layer-zip" {
  type        = "zip"
  source_dir  = "${path.module}/lamda/"
  output_path = "cognito_layer.zip"
}

resource "aws_lambda_layer_version" "cognito-layer" {
  layer_name       = "cognito_layer"
  s3_bucket = aws_s3_bucket_object.lambda_layer.bucket
  s3_key = aws_s3_bucket_object.lambda_layer.key
  source_code_hash = data.archive_file.cognito-layer-zip.output_base64sha256
  compatible_runtimes = ["python3.7"]
}
