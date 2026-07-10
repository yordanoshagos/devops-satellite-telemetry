FROM nginx:1.27-alpine

# curl is used by the compose healthcheck (see docker-compose*.yml). It is
# already present in nginx:1.27-alpine today, but installing it explicitly
# guards against a future upstream base image dropping it and turning the
# healthcheck into a silent failure.
RUN apk add --no-cache curl

# Bake in the docker-mode nginx config as a sensible default; the compose
# files also bind-mount the same file so live edits still work without a
# rebuild. Runtime bind-mount wins over this COPY.
COPY nginx-docker.conf /etc/nginx/conf.d/default.conf
