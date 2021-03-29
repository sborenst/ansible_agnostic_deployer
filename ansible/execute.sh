#!/bin/sh
TARGET_HOST="bastion.ab69.sandbox60.opentlc.com"
OCP_USERNAME="snandaku-redhat.com"
SSH_USER="snandaku-redhat.com"
SSH_PRIVATE_KEY="id_rsa"
GUID="snandaku"

WORKLOAD="ocp4-workload-cnad-app-modernization"

ansible-playbook -v -i ${TARGET_HOST}, ./configs/ocp-workloads/ocp-workload.yml \
                 -e"ansible_ssh_private_key_file=~/.ssh/${SSH_PRIVATE_KEY}" \
                 -e"ansible_ssh_user=${SSH_USER}" \
                 -e"ANSIBLE_REPO_PATH=`pwd`" \
                 -e"ocp_username=${OCP_USERNAME}" \
                 -e"ocp_workload=${WORKLOAD}" \
                 -e"guid=${GUID}" \
                 -e"ocp_user_needs_quota=true" \
                 -e"ocp_master=master.cluster-ab69.ab69.sandbox60.opentlc.com" \
                 -e"ocp_apps_domain=apps.cluster-ab69.ab69.sandbox60.opentlc.com" \
                 -e"ACTION=create" \
