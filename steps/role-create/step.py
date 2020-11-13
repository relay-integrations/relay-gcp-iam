#!/usr/bin/env python

import json
import sys
import requests
import googleapiclient.discovery

from google.oauth2 import service_account
from relay_sdk import Interface, Dynamic as D


def get_or_default(path, default=None):
    try:
        return relay.get(path)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 422:
            return default
        raise


def slice(orig, keys):
    return {key: orig[key] for key in keys if key in orig}


def get_credentials(connection):
    # For security purposes we whitelist the keys that can be fed in to the
    # google oauth library. This prevents workflow users from feeding arbitrary
    # data in to that library.
    service_account_info_keys = [
        "type",
        "project_id",
        "private_key_id",
        "private_key",
        "client_email",
        "client_id",
        "auth_uri",
        "token_uri",
        "auth_provider_x509_cert_url",
        "client_x509_cert_url",
    ]

    print("Getting service account info...")
    service_account_info = slice(json.loads(
        connection['serviceAccountKey']
    ), service_account_info_keys)

    return service_account.Credentials.from_service_account_info(service_account_info)


def get_client(product, version, credentials):
    print("Initiating %s client..." % product)
    return googleapiclient.discovery.build(product, version, credentials=credentials)


def create_role(client, project, name, title, description, permissions):
    body = {
        'roleId': name,
        'role': {
            'title': title,
            'description': description,
            'includedPermissions': permissions,
        },
    }

    print("Creating role with %s..." % body)
    result = client.create(parent='projects/%s' % project, body=body).execute()
    print("Result:")
    print(result)

    # These are the keys that we're going to cherry-pick out of the result.
    # We're explicit about the keys that we want to publish for documentation
    # purposes.
    # https://cloud.google.com/bigquery/docs/reference/rest/v2/datasets#Dataset
    return_keys = [
        "name",
        "title",
        "description",
        "includedPermissions",
    ]

    return_result = slice(result, return_keys)

    # Align naming with expected values
    return_result['permissions'] = return_result['includedPermissions']
    return_result.pop('includedPermissions', None)

    print("Converted Result:")
    print(return_result)

    return return_result


if __name__ == "__main__":
    relay = Interface()

    credentials = get_credentials(relay.get(D.google.connection))
    project = get_or_default(D.google.project, credentials.project_id)
    name = relay.get(D.name)
    title = get_or_default(D.title, name)
    description = get_or_default(D.description, None)
    permissions = relay.get(D.permissions)


    if not name:
        print("Missing `name` parameter on step configuration.")
        sys.exit(1)
    if not project:
        print("Missing `google.project` parameter on step configuration and no project was found in the connection.")
        sys.exit(1)
    if not permissions:
        print("Missing `permissions` parameter on step configuration.")
        sys.exit(1)
    if not isinstance(permissions, list):
        print("Incorrect `permissions` type, must be a list.")
        sys.exit(1)

    client = get_client('iam', 'v1', credentials).projects().roles()

    role = create_role(client, project, name, title, description, permissions)
    if role is None:
        print('role failed create!')
        sys.exit(1)

    print("Success!\n")
    print('\nAdding role to the output `role`')
    print(role)
    relay.outputs.set("role", role)
