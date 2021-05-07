#!/bin/bash 
set -xe

#export PATH=/home/admin/crc-linux-1.8.0-amd64:$PATH
crc config set consent-telemetry yes
# Disabling libvirt check so that it can be installed in nested virt
crc config set skip-check-libvirt-installed true
crc setup --log-level debug