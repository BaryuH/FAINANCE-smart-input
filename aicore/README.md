# FAINANCE Smart Input

Hướng dẫn triển khai và sử dụng hệ thống **FAINANCE-smart-input** trên máy chủ Linux.

---

## Yêu cầu hệ thống

- Hệ điều hành: Ubuntu / Debian Linux
- RAM: Tối thiểu 8GB
- GPU: NVIDIA RTX 3060 hoặc tương đương (để chạy ASR và OCR hiệu quả)
- Python: 3.11 (cài qua Miniconda)
- Quyền truy cập: `root` hoặc user có quyền `sudo`

---

## 1. Cài đặt môi trường hệ thống

```bash
apt-get update
apt-get install -y sudo
sudo apt-get update
sudo apt-get install -y git vim wget curl rclone unzip zip tar
```

Cài thêm `screen`, `tmux` và `nginx`:

```bash
sudo apt-get install -y screen tmux nginx
```

---

## 2. Clone dự án

```bash
cd /root
git clone <repo-url> FAINANCE-smart-input
cd /root/FAINANCE-smart-input
```

> Thay `<repo-url>` bằng đường dẫn repository thực tế.

---

## 3. Cài đặt Miniconda

```bash
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
source ~/miniconda3/bin/activate
conda --version
```

---

## 4. Cấu hình biến môi trường

Sao chép file mẫu và điền đầy đủ các giá trị:

```bash
cp .env_example .env
vim .env
```

Nội dung file `.env` cần điền:

```dotenv
# Ollama
OLLAMA_HOST=http://127.0.0.1:11434     # Địa chỉ Ollama server
OLLAMA_API_KEY=                         # API key nếu có (để trống nếu chạy local)
OLLAMA_MODEL=gemma4:31b-cloud          # Tên model sẽ sử dụng
OLLAMA_TIMEOUT_SECONDS=60              # Timeout (giây) cho mỗi request
```

> ⚠️ **Lưu ý:** Không commit file `.env` lên Git. File này đã được thêm vào `.gitignore`.

---

## 5. Tạo môi trường Python

```bash
conda create -n main python=3.11 -y
conda activate main
pip install -r requirements.txt
```

---

## 5. Cấu hình Nginx

Tạo cấu hình reverse proxy để Nginx chuyển tiếp traffic từ cổng 80 đến ứng dụng tại cổng 8000:

```bash
sudo tee /etc/nginx/sites-available/default > /dev/null << 'EOF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;

    server_name _;

    client_max_body_size 100M;

    proxy_read_timeout 300;
    proxy_connect_timeout 300;
    proxy_send_timeout 300;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Hỗ trợ WebSocket
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF
```

Kiểm tra và khởi động lại Nginx:

```bash
sudo nginx -t
sudo systemctl restart nginx
```

---

## 6. Khởi chạy ứng dụng

Sử dụng `screen` để giữ tiến trình chạy nền sau khi thoát SSH:

```bash
cd /root/FAINANCE-smart-input
conda activate main

screen -S fainance
python -m uvicorn aicore.api_server:app --host 0.0.0.0 --port 8000 --workers 1
```

Để thoát khỏi session `screen` mà **không dừng ứng dụng**, nhấn:

```
Ctrl + A, sau đó D
```

---

## 7. Quản lý tiến trình

| Lệnh | Mô tả |
|---|---|
| `screen -ls` | Liệt kê các session đang chạy |
| `screen -r fainance` | Kết nối lại vào session `fainance` |
| `Ctrl + A, D` | Thoát khỏi session (ứng dụng vẫn chạy) |
| `Ctrl + C` | Dừng ứng dụng (bên trong session) |

---

## 8. Truy cập ứng dụng

Sau khi khởi chạy, ứng dụng có thể truy cập tại:

```
http://<domain-hoặc-IP-máy-chủ>
```

> Nếu server đang dùng port mapping tùy chỉnh, truy cập theo:
> `http://<domain-của-bạn>:<port-đã-map>`

---

## 9. Cấu trúc dự án

```
FAINANCE-smart-input/
├───aicore
├───deploy
├───frontend-test
├───gipformer
```

---
