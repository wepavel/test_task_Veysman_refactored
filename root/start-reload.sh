#! /usr/bin/env sh
set -e

if [ -f /src/src/app.py ]; then
    DEFAULT_MODULE_NAME=src.app
elif [ -f /src/app.py ]; then
    DEFAULT_MODULE_NAME=app
fi


MODULE_NAME=${MODULE_NAME:-$DEFAULT_MODULE_NAME}
VARIABLE_NAME=${VARIABLE_NAME:-app}
export APP_MODULE=${APP_MODULE:-"$MODULE_NAME:$VARIABLE_NAME"}

HOST=${HOST:-0.0.0.0}
PORT=${PORT:-80}
LOG_LEVEL=${LOG_LEVEL:-info}


echo "MODULE_NAME" ${MODULE_NAME:-$DEFAULT_MODULE_NAME}
echo "APP_MODULE" $APP_MODULE

echo "Host: "$HOST "Port: "$PORT

exec uv run uvicorn --host 0.0.0.0 --port 8001 --log-level info --use-colors --log-config "log_config.json" --proxy-headers --forwarded-allow-ips='*' "$APP_MODULE"