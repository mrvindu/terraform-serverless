import logging
import json
import datetime
import decimal
import boto3
import traceback

akp_TEAM_EMAIL = 'akpapp@gmail.com'

logger = logging.getLogger()
logger.setLevel(logging.ERROR)

ses_client = boto3.client('ses', region_name='us-east-1')

def _get_function_details(context):
    if context:
        function_name = context.function_name
        function_version = context.function_version
        aws_request_id = context.aws_request_id
        return "function_name: {} <br/><br/> function_version: {} <br/><br/> aws_request_id: {}".format(function_name, function_version, aws_request_id)


def get_success_response(data, messages, code=200, context = None):
    if code >= 9000:
        _send_email(messages)

    return _get_response(200, code, data, messages)


def get_error_response(error_code, user_error_messages, log_error_msg, context = None):
    logger.error(log_error_msg)
    if error_code >= 9000:
        _send_email(user_error_messages, log_error_msg, context)
    return _get_response(505, error_code, {}, user_error_messages)


def _send_email(message, log_error_msg = None, context = None):
    error_message = message + '<br/>'

    if log_error_msg:
        error_message = error_message + log_error_msg + '<br/><br/>'

    error_message = error_message + traceback.format_exc()

    if context:
        function_info_details = _get_function_details(context)
        error_message = error_message + '<br/><br/><br/><p> akp API Info: <br/> ' + function_info_details + '</p>'

    ses_client.send_email(Source=akp_TEAM_EMAIL,
    Destination={
        'ToAddresses': [
            akp_TEAM_EMAIL
        ]
    },
    Message={
        'Subject': {
            'Data': 'Backend Error! - '
        },
        'Body': {
            'Html': {
                'Data': error_message
            }
        }
    })

def _get_response(api_code, code, data, messages):
    if isinstance(messages, str):
        messages = [messages]
    elif not isinstance(messages, list):
        logger.error("{} is of type {} not list".format(messages, type(messages)))
        return

    response = {
        'status': code,
        'date': datetime.datetime.now().isoformat(),
        'messages': messages
    }

    body = json.dumps(
        {
            "data": data,
            "response": response
        },
        cls=Encoder
    )

    return {
        "statusCode": api_code,
        "headers": {"Access-Control-Allow-Origin": "*"},
        "body": body
    }

class Encoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return int(obj)
        elif isinstance(obj, datetime.datetime):
            return obj.isoformat()
        elif isinstance(obj, datetime.date):
            return obj.isoformat()
        return super(Encoder, self).default(obj)
