#!/bin/sh
# Writes the S3 identity file from environment variables, then starts SeaweedFS.
set -eu
mkdir -p /data/config
cat > /data/config/s3.json <<JSON
{"identities":[{"name":"farm-api","credentials":[{"accessKey":"${S3_ACCESS_KEY}","secretKey":"${S3_SECRET_KEY}"}],"actions":["Read","Write","List","Tagging"]}]}
JSON
exec weed server -dir=/data -ip.bind=0.0.0.0 -s3 -s3.port=8333 -s3.config=/data/config/s3.json -volume.max=0
