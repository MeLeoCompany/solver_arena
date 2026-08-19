#!/bin/sh
set -e

WEBROOT=/var/www/certbot
mkdir -p "$WEBROOT"

if [ -z "$DOMAIN" ]; then
    echo "=================================================================="
    echo "  ВНИМАНИЕ: DOMAIN не задан в .env — сервер запускается по HTTP,"
    echo "  без шифрования. Подходит для локальной проверки, но НЕ для"
    echo "  деплоя, доступного из интернета — там задайте DOMAIN и"
    echo "  CERTBOT_EMAIL, чтобы поднялся HTTPS через Let's Encrypt."
    echo "=================================================================="
    cp /etc/nginx/templates/http.conf /etc/nginx/conf.d/default.conf
    exec nginx -g 'daemon off;'
fi

CERT_PATH="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"

if [ ! -f "$CERT_PATH" ]; then
    echo "Сертификат для $DOMAIN не найден — получаем через certbot..."
    envsubst '$DOMAIN' < /etc/nginx/templates/bootstrap.conf.template > /etc/nginx/conf.d/default.conf
    nginx -g 'daemon off;' &
    NGINX_PID=$!
    sleep 2

    certbot certonly --webroot -w "$WEBROOT" -d "$DOMAIN" \
        --email "$CERTBOT_EMAIL" --agree-tos --non-interactive

    kill "$NGINX_PID"
    wait "$NGINX_PID" 2>/dev/null || true
fi

envsubst '$DOMAIN' < /etc/nginx/templates/https.conf.template > /etc/nginx/conf.d/default.conf

# Периодическое продление — certbot сам не продлевает истекающие
# сертификаты в фоне, кто-то должен звать `certbot renew` регулярно.
( while true; do
    sleep 12h
    certbot renew --quiet --webroot -w "$WEBROOT" && nginx -s reload
done ) &

exec nginx -g 'daemon off;'
