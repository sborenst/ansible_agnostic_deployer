#!/bin/bash

usage() {
    echo "$0 CONFIG [STAGE]"
    echo
    echo "CONFIG: ALL | ocp-workshop | ocp-demo-lab | ans-tower-lab | ..."
    echo "STAGE: test | prod | rhte"
}

if [ -z "${1}" ]; then
    usage
    exit 1
fi

set -u -o pipefail

ORIG=$(cd $(dirname $0); pwd)

prompt_continue() {
    # call with a prompt string or use a default
    read -r -p "${1:-Continue? [Y/n]} " response

    if [ -z "${response}" ]; then
        true
    else
        case "${response}" in
            yes|y|Y|Yes|YES) true ;;
            *) false ;;
        esac
    fi
}

configs=$1
stage="${2:-}"

if [ "${configs}" = "ALL" ]; then
    configs=$(ls ${ORIG}/../ansible/configs)
fi

git log -1
echo
echo "About to tag this commit."
prompt_continue || exit 0

for config in ${configs}; do
    if [[ -n "${stage}" ]]; then
        tagname="${config}-${stage}"
        if echo "${tagname}" | grep -q -e '-prod-prod' -e '-test-test'; then
            echo
            echo "ERROR: ${tagname} has 'prod' or 'test' twice, please use prod only in the second parameter."
            echo
            exit 1
        fi
    else
        tagname="${config}"
    fi

    last=$(git tag -l | egrep "^${tagname}-([0-9]+\.[0-9]+(\.[0-9]+)?)$" | sort -V | tail -n 1 | egrep -o '[0-9]+\.[0-9]+(\.[0-9]+)?$')

    if [ -z "${last}" ]; then
        echo "INFO: no version found for ${config}, skipping"
        echo "Do you want to create it ?"
        prompt_continue || continue

        next_tag=${tagname}-0.0.1
    else
        major=$(echo $last | cut -f1 -d.)
        minor=$(echo $last | cut -f2 -d.)
        patch=$(echo $last | cut -f3 -d.)
	if [[ -n "${patch}" ]]; then
            next_tag=${tagname}-${major}.${minor}.$(( patch + 1))
	else
            next_tag=${tagname}-${major}.$(( minor + 1))
	fi
    fi

    echo "will now perform 'git tag ${next_tag}'"
    prompt_continue || continue

    git tag ${next_tag}

    echo "will now perform 'git push origin ${next_tag}"
    prompt_continue || continue
    git push origin ${next_tag}
done
