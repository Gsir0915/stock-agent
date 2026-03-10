#!/bin/bash
# 飞书机器人部署脚本（腾讯云服务器）
# 使用方法：scp deploy.sh root@your-server:/tmp/ && ssh root@your-server "bash /tmp/deploy.sh"

set -e

echo "=== 飞书机器人部署脚本 ==="

# 配置变量
INSTALL_DIR="/opt/stock-agent"
PYTHON_VENV="$INSTALL_DIR/venv"
SERVICE_NAME="stock-bot"
USE_SSL="${1:-no}"  # 第一个参数为 yes 时配置 SSL

# 1. 安装系统依赖
echo "[1/6] 安装系统依赖..."
apt update
apt install -y python3 python3-pip python3-venv git nginx jq curl

# 2. 创建安装目录
echo "[2/6] 创建目录..."
mkdir -p $INSTALL_DIR

# 3. 克隆代码（如果未存在）
echo "[3/6] 准备代码..."
if [ ! -f "$INSTALL_DIR/requirements.txt" ]; then
    echo "请将代码上传到 $INSTALL_DIR 或设置 Git 仓库地址"
    read -p "Git 仓库地址（留空跳过）：" GIT_REPO
    if [ -n "$GIT_REPO" ]; then
        git clone $GIT_REPO $INSTALL_DIR
    fi
fi

cd $INSTALL_DIR

# 4. 配置 Python 虚拟环境
echo "[4/7] 配置 Python 环境..."
python3 -m venv $PYTHON_VENV
source $PYTHON_VENV/bin/activate
pip install --upgrade pip

# 5. 安装应用依赖
echo "[5/7] 安装应用依赖..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "错误：requirements.txt 不存在"
    exit 1
fi

# 6. 创建 systemd 服务
echo "[6/7] 配置 systemd 服务..."
cat > /etc/systemd/system/$SERVICE_NAME.service << EOF
[Unit]
Description=Feishu Stock Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$PYTHON_VENV/bin"
ExecStart=$PYTHON_VENV/bin/python -m app.bot --port 8080
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable $SERVICE_NAME

# 7. 配置 Nginx 或 cloudflared
echo "[7/7] 配置 Web 服务..."

if [ "$USE_SSL" = "yes" ]; then
    # Nginx + SSL 配置
    echo "正在配置 Nginx + SSL..."
    echo ""
    read -p "请输入域名：" DOMAIN_NAME

    if [ -z "$DOMAIN_NAME" ]; then
        echo "错误：域名不能为空"
        exit 1
    fi

    # 创建 Nginx 配置
    cat > /etc/nginx/sites-available/stock-bot << NGINX_EOF
server {
    listen 80;
    server_name $DOMAIN_NAME;

    # ACME 挑战用于 Let's Encrypt
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location /feishu/event {
        proxy_pass http://127.0.0.1:8080/feishu/event;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }

    location /health {
        proxy_pass http://127.0.0.1:8080/health;
    }
}
NGINX_EOF

    ln -sf /etc/nginx/sites-available/stock-bot /etc/nginx/sites-enabled/
    nginx -t && systemctl reload nginx

    echo ""
    echo "Nginx 配置完成！"
    echo "请使用 certbot 申请 SSL 证书:"
    echo "  certbot --nginx -d $DOMAIN_NAME"
    echo ""
else
    # cloudflared 配置
    echo "正在安装 cloudflared..."
    wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
    chmod +x cloudflared-linux-amd64
    mv cloudflared-linux-amd64 /usr/local/bin/cloudflared

    # 创建 cloudflared 服务
    cat > /etc/systemd/system/cloudflared-tunnel.service << 'CLOUDFLARED_EOF'
[Unit]
Description=Cloudflare Tunnel for Stock Bot
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/cloudflared tunnel --url http://localhost:8080
Restart=always

[Install]
WantedBy=multi-user.target
CLOUDFLARED_EOF

    systemctl daemon-reload
    systemctl enable cloudflared-tunnel

    echo ""
    echo "cloudflared 已安装！"
    echo "启动后运行：systemctl start cloudflared-tunnel"
    echo "查看隧道 URL: journalctl -u cloudflared-tunnel -f"
fi

echo ""
echo "=== 部署完成 ==="
echo ""
echo "后续步骤："
echo "1. 配置 .env 文件：cd $INSTALL_DIR && vim .env"
if [ "$USE_SSL" = "yes" ]; then
    echo "2. 申请 SSL 证书：certbot --nginx -d your-domain.com"
    echo "3. 启动服务：systemctl start $SERVICE_NAME"
    echo "4. 在飞书开放平台配置 URL: https://your-domain.com/feishu/event"
else
    echo "2. 启动服务：systemctl start $SERVICE_NAME cloudflared-tunnel"
    echo "3. 查看隧道 URL: journalctl -u cloudflared-tunnel -f"
    echo "4. 在飞书开放平台配置 URL: https://xxx.trycloudflare.com/feishu/event"
fi
echo ""
echo "查看日志：journalctl -u $SERVICE_NAME -f"
