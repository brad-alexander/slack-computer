#! /usr/bin/env bash
if [ -z "${CERTBOT_DOMAIN}" ]; then
    certbot certonly --standalone -n --domains $CERTBOT_DOMAIN --agree-tos --email $CERTBOT_EMAIL
else
    echo "CERTBOT_DOMAIN not set, not generating certificate"
fi