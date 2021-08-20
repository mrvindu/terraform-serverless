
def list_users(user_filter):
    list_users_response = cognito_client.list_users(UserPoolId=COGNITO_USER_POOL_ID, Filter=user_filter)
    users = list_users_response['Users']
    while 'PaginationToken' in list_users_response:
        list_users_response = cognito_client.list_users(UserPoolId=COGNITO_USER_POOL_ID, Filter=user_filter,
                                                        PaginationToken=list_users_response['PaginationToken'])
        users += list_users_response['Users']
    return users




