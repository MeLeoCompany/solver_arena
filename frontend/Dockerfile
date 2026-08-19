# Build context is the repo root (see docker-compose.yml) — needed so this
# image can pick up deploy/nginx/ alongside the frontend sources.
FROM node:20-slim AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM nginx:alpine

# certbot — issues/renews the Let's Encrypt cert when DOMAIN is set (see
# deploy/nginx/entrypoint.sh); envsubst (gettext) — renders the ${DOMAIN}
# placeholder in the nginx templates without touching nginx's own runtime
# $variables (host, uri, etc).
RUN apk add --no-cache certbot gettext

COPY --from=build /app/dist /usr/share/nginx/html
COPY deploy/nginx/http.conf /etc/nginx/templates/http.conf
COPY deploy/nginx/bootstrap.conf.template /etc/nginx/templates/bootstrap.conf.template
COPY deploy/nginx/https.conf.template /etc/nginx/templates/https.conf.template
COPY deploy/nginx/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 80 443
ENTRYPOINT ["/entrypoint.sh"]
