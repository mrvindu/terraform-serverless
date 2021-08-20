import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.ERROR)


def get_method(event, supported_methods, api):
    if 'httpMethod' not in event:
        logger.error("httpMethod not present in event {} for api {}".format(event, api))
        return 'HTTP method not present in {}'.format(api)

    method = event['httpMethod']
    if method not in supported_methods:
        error_msg = "Unsupported method: {} on {} API".format(method, api)
        logger.error(error_msg)
        return error_msg

    return method


def check_request_params(event, expected_request_params):
    body = json.loads(event['body'] if 'body' in event and event['body'] else '{}')
    if not expected_request_params:
        return body

    missing_params = []
    for expected_request_param in expected_request_params:
        if expected_request_param not in body:
            missing_params.append(expected_request_param)

    if len(missing_params) != 0:
        body['missing_params'] = missing_params

    return body


def get_body(event, expected_request_params):
    return check_request_params(event, expected_request_params)


def get_query_params(event, expected_query_params):
    query_params = event['queryStringParameters'] if 'queryStringParameters' and event['queryStringParameters'] else {}
    if not expected_query_params:
        return query_params

    query_params['missing_params'] = [eqp for eqp in expected_query_params if eqp not in query_params]

    return query_params


def get_username(event):
    if 'requestContext' not in event:
        logger.error('requestContext not present in event {}'.format(event))
        return

    request_context = event['requestContext']
    if 'authorizer' not in request_context:
        logger.error('authorizer not present in event request context {}'.format(request_context))
        return

    authorizer = request_context['authorizer']
    if 'claims' not in authorizer:
        logger.error('claims not present in event request context authorizer {}'.format(authorizer))
        return

    claims = authorizer['claims']
    if 'cognito:username' not in claims:
        logger.error('cognito:username not present in event request context authorizer claims {}'.format(claims))
        return

    return claims['cognito:username']


def get_id_token(event):
    if 'headers' not in event:
        logger.error('headers not present in event {}'.format(event))
        return

    if 'Authorization' not in event['headers']:
        logger.error('Authorization not present in event headers {}'.format(event))
        return

    return event['headers']['Authorization'].split()[1]
