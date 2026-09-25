# Nginx + uWSGI 佈署筆記

## 安裝

```bash
# Linux
sudo apt install nginx
# 或 macOS
brew install nginx

pip install uwsgi
```

## uWSGI 操作

```bash
# 啟動
uwsgi --ini uwsgi.ini

# 停止
uwsgi --stop uwsgi.pid

# 查看狀態
ps -ef | grep uwsgi
```

## Nginx 操作

```bash
# 測試設定
sudo nginx -t -c /path/to/nginx.conf

# 啟動
sudo nginx -c /path/to/nginx.conf

# 優雅退出
sudo nginx -s quit

# 重載
sudo nginx -s reload

# 查看狀態
ps -ef | grep nginx
```

## 常見問題

若上傳檔案出現 Permission denied：
```
"/run/nginx/client_body_temp/..." failed (13: Permission denied)
```
請執行：
```bash
sudo chmod -R 775 /run/nginx/client_body_temp
```
