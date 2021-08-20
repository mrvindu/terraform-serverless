import boto3
from botocore.exceptions import ClientError
import logging

import hmac
import hashlib
import base64
import uuid

import akp_db as db

logger = logging.getLogger()
logger.setLevel(logging.ERROR)

cognito_client = boto3.client('cognito-idp')
kms_client = boto3.client('kms')

COGNITO_USER_POOL_ID = 'us-east-2_kltUtjMuC'
USER_ATTRIBUTES_TO_UPDATE = ['name', 'email', 'country', 'city', 'birthdate', 'gender', 'latitude', 'longitude']
AVATAR_TABLE = 'avatars'


def admin_get_user(username):
    return cognito_client.admin_get_user(UserPoolId=COGNITO_USER_POOL_ID, Username=username)


def admin_enable_user(username):
    return cognito_client.admin_enable_user(UserPoolId=COGNITO_USER_POOL_ID, Username=username)


def admin_disable_user(username):
    return cognito_client.admin_disable_user(UserPoolId=COGNITO_USER_POOL_ID, Username=username)


def has_updated_profile(username, access_token=None):
    if access_token:
        user = cognito_client.get_user(AccessToken=access_token)
    else:
        user = admin_get_user(username)

    if not user or 'UserAttributes' not in user:
        return False

    user_attributes = user['UserAttributes']
    user_attribute_names = [ua['Name'].replace('custom:', '') for ua in user_attributes]
    user_attribute_values = [ua['Value'] for ua in user_attributes]
    avatar_key = db.get('avatar_key', AVATAR_TABLE, 'username', username, 1)
    is_default_avatar = not avatar_key or 'default_avatar' in avatar_key[0]['avatar_key']
    all_names = all(uan in user_attribute_names for uan in USER_ATTRIBUTES_TO_UPDATE)
    all_values = all(uav is not None for uav in user_attribute_values)
    return all_names and all_values and not is_default_avatar


def admin_create_user(username, user_attributes):
    return cognito_client.admin_create_user(UserPoolId=COGNITO_USER_POOL_ID,
                                            Username=username,
                                            UserAttributes=user_attributes,
                                            DesiredDeliveryMediums=['EMAIL'])


def admin_delete_user(username):
    return cognito_client.admin_delete_user(UserPoolId=COGNITO_USER_POOL_ID, Username=username)


def admin_update_user_attributes(username, user_attributes):
    return cognito_client.admin_update_user_attributes(UserPoolId=COGNITO_USER_POOL_ID, Username=username,
                                                       UserAttributes=user_attributes)


def get_email_for_user(username):
    cognito_user = admin_get_user(username)
    if 'UserAttributes' not in cognito_user:
        return None

    for attribute in cognito_user['UserAttributes']:
        if attribute['Name'] != 'email':
            continue

        return attribute['Value']


def change_password(previous_password, proposed_password, access_token):
    decrypted_previous_password = kms_client.decrypt(CiphertextBlob=bytearray([p % 256 for p in previous_password]))['Plaintext'].decode('utf-8')
    decrypted_proposed_password = kms_client.decrypt(CiphertextBlob=bytearray([p % 256 for p in proposed_password]))['Plaintext'].decode('utf-8')
    return cognito_client.change_password(PreviousPassword=decrypted_previous_password,
                                          ProposedPassword=decrypted_proposed_password,
                                          AccessToken=access_token)


def list_users(user_filter):
    list_users_response = cognito_client.list_users(UserPoolId=COGNITO_USER_POOL_ID, Filter=user_filter)
    users = list_users_response['Users']
    while 'PaginationToken' in list_users_response:
        list_users_response = cognito_client.list_users(UserPoolId=COGNITO_USER_POOL_ID, Filter=user_filter,
                                                        PaginationToken=list_users_response['PaginationToken'])
        users += list_users_response['Users']
    return users


def initiate_auth(username, password, client, client_secret, auth_flow, refresh_token=''):
    client_details = _get_client_details(client)
    if not client_details:
        raise ClientError('Cognito client details is None for client {}'.format(client), 'initiate_auth')
    decrypted_password = kms_client.decrypt(CiphertextBlob=bytearray([p % 256 for p in password]))['Plaintext'].decode('utf-8') if password else ''

    clientId = client_details['ClientId']
    clientSecret = client_details['ClientSecret']
    secretHash = _get_secret_hash(username, clientId, clientSecret)

    return cognito_client.initiate_auth(AuthFlow=auth_flow,
                                        AuthParameters={
                                            'USERNAME': username,
                                            'PASSWORD': decrypted_password,
                                            'SECRET_HASH': secretHash,
                                            'REFRESH_TOKEN': refresh_token
                                        },
                                        ClientId=client_details['ClientId'])


def respond_to_auth_challenge(challenge_name, session, challenge_responses, client, client_secret):
    client_details = _get_client_details(client)
    if not client_details:
        raise ClientError('Cognito client details is None for client {}'.format(client), 'initiate_auth')

    clientId = client_details['ClientId']
    clientSecret = client_details['ClientSecret']
    secretHash = _get_secret_hash(challenge_name, clientId, clientSecret)

    challenge_responses['SECRET_HASH'] = secretHash
    password = challenge_responses['NEW_PASSWORD']
    challenge_responses['NEW_PASSWORD'] = kms_client.decrypt(CiphertextBlob=bytearray([p % 256 for p in password]))['Plaintext'].decode('utf-8') if password else ''

    return cognito_client.respond_to_auth_challenge(ClientId=clientId, ChallengeName=challenge_name,
                                                    Session=session, ChallengeResponses=challenge_responses)


def forgot_password(username, client, client_secret):
    # username = _get_username(username)

    client_details = _get_client_details(client)
    if not client_details:
        raise ClientError('Cognito client details is None for client {}'.format(client), 'forgot_password')

    clientId = client_details['ClientId']
    clientSecret = client_details['ClientSecret']
    secretHash = _get_secret_hash(username, clientId, clientSecret)

    return cognito_client.forgot_password(Username=username, ClientId=clientId,
                                          SecretHash=secretHash)


def confirm_forgot_password(username, client, client_secret, confirmation_code, password):
    # username = _get_username(username)

    client_details = _get_client_details(client)
    if not client_details:
        raise ClientError('Cognito client details is None for client {}'.format(client), 'confirm_forgot_password')
    decrypted_password = kms_client.decrypt(CiphertextBlob=bytearray([p % 256 for p in password]))['Plaintext'].decode('utf-8')

    clientId = client_details['ClientId']
    clientSecret = client_details['ClientSecret']
    secretHash = _get_secret_hash(username, clientId, clientSecret)

    return cognito_client.confirm_forgot_password(Username=username,
                                                  ClientId=clientId,
                                                  SecretHash=secretHash,
                                                  ConfirmationCode=confirmation_code,
                                                  Password=decrypted_password)


def resend_confirmation_code(username, client, client_secret):
    client_details = _get_client_details(client)
    if not client_details:
        raise ClientError('Cognito client details is None for client {}'.format(client), 'resend_confirmation_code')

    clientId = client_details['ClientId']
    clientSecret = client_details['ClientSecret']
    secretHash = _get_secret_hash(username, clientId, clientSecret)

    return cognito_client.resend_confirmation_code(Username=username,
                                                   ClientId=clientId,
                                                   SecretHash=secretHash)


def sign_up(username, password, client, client_secret, user_attributes):
    client_details = _get_client_details(client)
    if not client_details:
        raise ClientError('Cognito client details is None for client {}'.format(client), 'resend_confirmation_code')
    decrypted_password = kms_client.decrypt(CiphertextBlob=bytearray([p % 256 for p in password]))['Plaintext'].decode('utf-8')

    clientId = client_details['ClientId']
    clientSecret = client_details['ClientSecret']
    secretHash = _get_secret_hash(username, clientId, clientSecret)

    return cognito_client.sign_up(Username=username,
                                  Password=decrypted_password,
                                  ClientId=clientId,
                                  SecretHash=secretHash,
                                  UserAttributes=user_attributes)


def confirm_sign_up(username, client, client_secret, confirmation_code):
    client_details = _get_client_details(client)
    if not client_details:
        raise ClientError('Cognito client details is None for client {}'.format(client), 'confirm_sign_up')

    clientId = client_details['ClientId']
    clientSecret = client_details['ClientSecret']
    secretHash = _get_secret_hash(username, clientId, clientSecret)
    return cognito_client.confirm_sign_up(Username=username,
                                          ClientId=clientId,
                                          SecretHash=secretHash,
                                          ConfirmationCode=confirmation_code)


def verify_user_attribute(access_token, attribute_name, code):
    return cognito_client.verify_user_attribute(AccessToken=access_token, AttributeName=attribute_name, Code=code)


def update_user_attributes(access_token, user_attributes):
    return cognito_client.update_user_attributes(AccessToken=access_token, UserAttributes=user_attributes)


def get_user_attribute_verification_code(access_token, attribute_name):
    return cognito_client.get_user_attribute_verification_code(AccessToken=access_token, AttributeName=attribute_name)


def _get_client_details(client):
    user_pool_clients = cognito_client.list_user_pool_clients(UserPoolId=COGNITO_USER_POOL_ID)
    user_pool_clients['UserPoolClients'] = user_pool_clients['UserPoolClients'] if 'UserPoolClients' in user_pool_clients else []
    for user_pool_client in user_pool_clients['UserPoolClients']:
        if user_pool_client['ClientName'].lower() == client.lower():
            user_pool_client = cognito_client.describe_user_pool_client(UserPoolId=COGNITO_USER_POOL_ID,
                                                                        ClientId=user_pool_client['ClientId'])
            return user_pool_client['UserPoolClient'] if 'UserPoolClient' in user_pool_client else None

def _get_secret_hash(username, client_id, client_secret):
    msg = username + client_id
    dig = hmac.new(str(client_secret).encode('utf-8'),
    msg = str(msg).encode('utf-8'), digestmod=hashlib.sha256).digest()
    d2 = base64.b64encode(dig).decode()
    return d2