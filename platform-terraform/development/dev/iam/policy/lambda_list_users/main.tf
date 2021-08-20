terraform {
  backend "s3" {
    encrypt        = true
    bucket         = "akp-new-terraform-remote-state-storage-s3"
    dynamodb_table = "terraform-state-lock-dynamo"
    region         = "us-east-2"
    key            = "iam/policy/lambda-list-users/terraform.state"
  }
}

data "aws_cognito_user_pools" "main-user-pool" {
  name = "akp-users"
}

resource "aws_iam_policy" "policy" {
  name        = "LambdaListUsersPolicy"
  path        = "/"
  description = "Policy to be attached to role assumed by the list-users lambda"

  policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "cognito-idp:ListUsers"
            ],
            "Resource": "${join("", data.aws_cognito_user_pools.main-user-pool.arns)}"
        }
    ]
}
EOF
}
