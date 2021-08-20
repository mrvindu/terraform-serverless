terraform {
  backend "s3" {
    encrypt        = true
    bucket         = "akp-new-terraform-remote-state-storage-s3"
    dynamodb_table = "terraform-state-lock-dynamo"
    region         = "us-east-2"
    key            = "iam/role/lambda-list-users/terraform.state"
  }
}

resource "aws_iam_role" "lambda-list-users-role" {
  name = "LambdaListUsersRole"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF

}

resource "aws_iam_role_policy_attachment" "lambda-list-users-role-attach-lambda-base-policy" {
  role       = aws_iam_role.lambda-list-users-role.name
  policy_arn = var.lambda_base_policy_arn
}

resource "aws_iam_role_policy_attachment" "lambda-list-users-role-attach-lambda-list-users-policy" {
  role       = aws_iam_role.lambda-list-users-role.name
  policy_arn = var.lambda_list_users_policy_arn
}

