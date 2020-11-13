#!/usr/bin/env python

import json
import sys
import requests
import googleapiclient.discovery

from google.oauth2 import service_account
from relay_sdk import Interface, Dynamic as D


def slice(orig, keys):
    return {key: orig[key] for key in keys if key in orig}


def get_binding(policy, role, condition):
    binding = {}
    for b in policy["bindings"]:
        if "role" in b and b["role"] == role:
            if ("condition" not in b and condition is None) or ("condition" in b and b["condition"] == condition):
                binding = b
                break
    if binding:
        print(f'Role: {(binding["role"])}')
        print("Members: ")
        for m in binding["members"]:
            print(f'[{m}]')

    return binding


def get_policy(crm_service, project_id, version=3):
    """Gets IAM policy for a project."""

    policy = (
        crm_service.projects()
        .getIamPolicy(
            resource=project_id,
            body={"options": {"requestedPolicyVersion": version}},
        )
        .execute()
    )
    return policy


def set_policy(crm_service, project_id, policy):
    """Sets IAM policy for a project."""

    policy['version'] = 3
    return (
        crm_service.projects()
        .setIamPolicy(resource=project_id, body={"policy": policy})
        .execute()
    )


def get_client(product, version, credentials):
    print("Initiating %s client..." % product)
    return googleapiclient.discovery.build(product, version, credentials=credentials, cache_discovery=False)


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


def modify_policy_add_role(crm_service, project_id, role, members, condition):
    """Adds a new role binding to a policy."""

    policy = get_policy(crm_service, project_id)

    binding = get_binding(policy, role, condition)
    if binding:
        print("Extending role with %s" % ', '.join(members))
        binding["members"].extend(members)
    else:
        print("Creating binding of role %s with members %s" % (role, ', '.join(members)))
        binding = {
            "role": role,
            "members": members,
            "condition": condition,
        }
        policy["bindings"].append(binding)
    return set_policy(crm_service, project_id, policy)


def modify_policy_remove_member(crm_service, project_id, role, members, condition):
    """Removes a  member from a role binding."""

    policy = get_policy(crm_service, project_id)

    binding = get_binding(policy, role, condition)
    for member in members:
        if binding and "members" in binding and member in binding["members"]:
            print("Removing binding of member %s in role %s" % (member, role))
            binding["members"].remove(member)

    return set_policy(crm_service, project_id, policy)


def get_or_default(path, default=None):
    try:
        return relay.get(path)
    except requests.exceptions.HTTPError as err:
        if err.response.status_code == 422:
            return default
        raise


if __name__ == "__main__":
    relay = Interface()

    credentials = get_credentials(relay.get(D.google.connection))
    project = get_or_default(D.google.project, credentials.project_id)
    role = relay.get(D.role)
    members = relay.get(D.members)
    condition = get_or_default(D.condition, None)

    if not project:
        print("Missing `google.project` parameter on step configuration and no project was found in the connection.")
        sys.exit(1)
    if not role:
        print("Missing `role` parameter on step configuration.")
        sys.exit(1)
    if not members:
        print("Missing `members` parameter on step configuration.")
        sys.exit(1)
    if not isinstance(members, list):
        members = [members]

    client = get_client("cloudresourcemanager", "v1", credentials)
    policy = modify_policy_add_role(client, project, role, members, condition)
    # policy = modify_policy_remove_member(client, project, role, members, condition)
    if policy is None:
        print('policy failed update!')
        sys.exit(1)
    print("Result:")
    print(policy)
    binding = get_binding(policy, role, condition)

    return_keys = [
        "role",
        "members",
        "condition",
    ]

    return_result = slice(binding, return_keys)

    print("Success!\n")
    print('\nAdding binding to the output `binding`:')
    print(return_result)
    relay.outputs.set("role", role)
