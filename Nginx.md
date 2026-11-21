# Nginx + uWSGI Deployment Notes

## Installation

```bash
# Linux
sudo apt install nginx
# or macOS
brew install nginx

pip install uwsgi
```

## uWSGI Operations

```bash
# Start
uwsgi --ini uwsgi.ini

# Stop
uwsgi --stop uwsgi.pid

# Check status
ps -ef | grep uwsgi
```

## Nginx Operations

```bash
# Test configuration
sudo nginx -t -c /path/to/nginx.conf

# Start
sudo nginx -c /path/to/nginx.conf

# Graceful shutdown
sudo nginx -s quit

# Reload
sudo nginx -s reload

# Check status
ps -ef | grep nginx
```

## Troubleshooting

If file uploads fail with `Permission denied`:
```
"/run/nginx/client_body_temp/..." failed (13: Permission denied)
```
Run:
```bash
sudo chmod -R 775 /run/nginx/client_body_temp
```
