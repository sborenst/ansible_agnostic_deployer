#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# MIT License

# Copyright: (c) 2020, Marcos Amorim <mamorim@redhat.com>
#                2020, Guillaume Core <gucore@redhat.com>

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from __future__ import absolute_import, division, print_function

# another datetime is imported from module_utils.basic too
from datetime import datetime as datetime_py

import os
from ansible.module_utils.basic import *
import yaml
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from cryptography import __version__  as crypto_version
import base64
import q
q("crypto version: " + crypto_version)

__metaclass__ = type

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: bitwarden
short_description: Get secrets from bitwarden
version_added: "2.10"
description:
    - This module connect to bitwarden using bw cli and get a list of secure notes and return a dict with all variables or import to ansible_facts
options:
    secrets:
        description: A list of bitwarden secure note names to be loaded
        required: true
        type: list
    username:
        description: Username to connect to bitwarden
        required: true
        type: str
    password:
        description: Password to connect to bitwarden
        required: true
        type: str
    salt:
        description: Salt used to transform the password into a key to encrypt the token locally. It is more secure to set one.
        required: false
        type: str
        default: SALT
    token_path:
        description: Path to store bitwarden token. The Token is encrypted symetrically using `password` and `salt`.
        required: false
        type: str
        default: ~/.bw_token
    vault_dir:
        description: Directory to store local vault.
        required: false
        type: str
        default: ~/bw-data
    cache:
        description: Time in minutes after which the cache expires and force sync with bitwarden
        required: false
        default: 1
        type: int
    include_vars:
        description: Include all `secrets` as variable
        required: false
        type: bool
        default: true

equirements:
    - "python >= 2.7"
    - "bw-cli"
    - "LibYAML"
author:
    - Marcos Amorim (@marcosmamorim)
    - Guillaume Core (@fridim)
'''

EXAMPLES = '''
- name: Get secret from bitwarden
  bitwarden:
    secrets:
      - secret_name_one
      - secret_name_two
    username: "bitwarden_username"
    password: "bitwarden_user_password"
    token_path: "~/.bw_token"
    cache: 30
    include_vars: true
- name: Get secret from bitwarden for another User without polluting the first user
  bitwarden:
    secrets:
      - secret_name_three
    username: "bitwarden_username2"
    password: "bitwarden_user_password2"
    vault_dir: "~/bw-user2"
    token_path: "~/bw-user2/token"
'''
RETURN = '''
'''

def fernet_generate_key(password, salt):
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend(),
    )

    return base64.urlsafe_b64encode(kdf.derive(password))

def fernet_encrypt(password, salt, message):
    key = fernet_generate_key(password.encode('utf-8'), salt.encode('utf-8'))
    f = Fernet(key)
    return f.encrypt(message.encode('utf-8')).decode('utf-8')

def fernet_decrypt(password, salt, message):
    key = fernet_generate_key(password.encode('utf-8'), salt.encode('utf-8'))
    f = Fernet(key)
    return f.decrypt(message.encode('utf-8')).decode('utf-8')

def save_token(module, token):
    secret_file = os.path.expanduser(module.params.get("token_path"))
    password = module.params.get("password")
    salt = module.params.get("salt")
    home_dir = os.path.dirname(secret_file)

    if not os.path.exists(home_dir):
        os.makedirs(home_dir)

    try:
        module.log("Saving token into {}".format(secret_file))
        f = open(secret_file, 'w')
        f.write(fernet_encrypt(password, salt, token))
        f.close()
    except Exception as e:
        module.fail_json(msg="Failed writing token file. Error message {}".format(e))


def read_token(module):
    secret_file = os.path.expanduser(module.params.get("token_path"))
    password = module.params.get("password")
    salt = module.params.get("salt")

    module.log("Reading token from file {}".format(secret_file))
    try:
        with open(secret_file, 'r') as reader:
            return fernet_decrypt(password, salt, reader.read())
    except:
        return None

def bw_sync(module, status, token):
    force_sync = module.params.get("cache")
    t_now = datetime_py.utcnow()
    # TODO: remove q
    q("Last sync {0}".format(status))
    t_last_sync = datetime_py.strptime(status['lastSync'], '%Y-%m-%dT%H:%M:%S.%fZ')
    delta = t_now - t_last_sync
    last_sync_min = int((delta.total_seconds() / 60))
    module.log("Last sync {0} minutes ago. Max is set to {1}".format(last_sync_min, force_sync))
    if last_sync_min > force_sync:
        module.log("Last sync {0} minutes ago reach out max sync time {1}".format(last_sync_min, force_sync))
        module.run_command("bw sync", environ_update=dict(BW_SESSION=token))


def bw_login(module):
    bw_user = module.params.get("username")
    bw_pass = module.params.get("password")

    module.log("New login username {}".format(bw_user))
    # pass password as stdin using data
    cmd = "bw login --raw {username}".format(username=bw_user)
    rc, out, err = module.run_command(cmd, check_rc=False, data=bw_pass)
    save_token(module, out)
    return out


def bw_unlock(module):
    bw_pass = module.params.get("password")

    module.log("Session is locked, unlocking")
    rc, token, err = module.run_command("bw unlock {password} --raw".format(password=bw_pass), check_rc=True)
    save_token(module, token)
    return token


def bw_get_status(module):
    module.log("Checking bw status")
    token = read_token(module)
    try:
        if token:
            rc, out, err = module.run_command("bw status --raw", environ_update=dict(BW_SESSION=token), check_rc=True)
        else:
            rc, out, err = module.run_command("bw status --raw", check_rc=True)
        if rc == 0:
            j_out = json.loads(out)
            return j_out
    except Exception as e:
        module.fail_json(msg="Error getting vault status. Error {}".format(e))

def get_token(module):
    module.log("Checking bw status")
    token = None

    status_all = bw_get_status(module)
    status = status_all['status']

    if status == 'locked':
        q("locked, unlock")
        token = bw_unlock(module)
    elif status == 'unauthenticated':
        q("unauthenticated, login")
        token = bw_login(module)
    elif status == 'unlocked':
        q("unlocked, read token")
        module.log("Reading token from file")
        token = read_token(module)

    return token

def parse_secret(module, result):
    variables = {}
    module.log("FULL JSON: {}".format(json.dumps(result)))
    if result['notes']:
        module.log("Parsing notes from secret")
        variables.update(yaml.load(result['notes']))

    if 'fields' in result and len(result['fields']) > 0:
        module.log("Parsing custom fields from secret")
        for f in result['fields']:
            variables.update({f['name']: f['value']})

    if 'login' in result:
        module.log("Parsing login from secret")
        login = result['login']
        variables.update({'username': login['username']})
        variables.update({'password': login['password']})

        urls = []
        if 'uris' in login:
            for url in login['uris']:
                urls.append(url['uri'])
            if len(urls) > 0:
                variables.update({'uris': urls})

    return variables


def run_bw(module, secret_name, token):
    # TODO: Parse error
    # TODO: Check if secret returned and create a way to warn the user about it
    rc, out, err = module.run_command(
        "bw get item '{}'".format(secret_name),
        environ_update=dict(BW_SESSION=token),
        check_rc=True
    )
    j_out = json.loads(out)
    variables = {}
    module.log("Current result {0}: {1}".format(secret_name, json.dumps(j_out)))
    variables.update(parse_secret(module, j_out))

    return variables


def get_secrets(module):
    secrets = module.params.get("secrets")
    include_vars = module.params.get("include_vars")
    d_secrets = {}
    token = get_token(module)
    status_all = bw_get_status(module)
    # Try to sync everytime
    bw_sync(module, status_all, token)

    for secret in secrets:
        module.log("Getting secret {}".format(secret))
        r = run_bw(module, secret, token)
        d_secrets.update(r)

    if include_vars:
        module.exit_json(changed=True, ansible_facts=d_secrets)
    else:
        module.exit_json(changed=True, secrets=d_secrets)


def run_module():
    module_args = dict(
        secrets=dict(type="list", required=True),
        username=dict(type="str", required=True),
        password=dict(type="str", required=True, no_log=True),
        salt=dict(type="str", required=False, default="SALT", no_log=True),
        token_path=dict(type="str", default="~/.bw_token",  no_log=True),
        cache=dict(type="int", default=1),
        include_vars=dict(type="bool", default="true", choices=BOOLEANS),
        vault_dir=dict(type="str", required=False, default="~/bw-data"),
    )

    module = AnsibleModule(module_args)

    os.environ["BITWARDENCLI_APPDATA_DIR"] = os.path.expanduser(module.params.get("vault_dir"))

    if module.check_mode:
        module.exit_json(msg="Operation skipped - running in check mode", changed=True)

    get_secrets(module)
    module.exit_json(failed=False)


def main():
    run_module()

if __name__ == '__main__':
    main()
