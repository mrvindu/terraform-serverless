
def handler(event, context):
    method_or_error = request.get_method(event, ["POST"], "list_users")
    if "POST" == method_or_error:
        body = request.get_body(event, POST_REQUEST_PARAMS)
        users = cognito.list_users(body['filter'].lower() if 'filter' in body else '')
        return response.get_success_response({'Users': users}, [], context)
    else:
        return response.get_error_response(9000, method_or_error, method_or_error, context)
