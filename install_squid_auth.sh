#!/bin/bash

# 用户可指定端口（默认3128）
PORT=${1:-3128}
USERNAME="proxyuser"
PASSWD_FILE="/etc/squid/passwd"

# 获取服务器公网 IP（用于测试提示）
SERVER_IP=$(curl -s ifconfig.me || hostname -I | awk '{print $1}')

echo "🚀 安装 Squid 和 apache2-utils..."
sudo apt update && sudo apt install -y squid apache2-utils

echo "👤 创建代理认证用户 '$USERNAME'..."
sudo htpasswd -c $PASSWD_FILE $USERNAME

echo "🗂️ 备份原 squid.conf 到 /etc/squid/squid.conf.bak"
sudo cp /etc/squid/squid.conf /etc/squid/squid.conf.bak

echo "📝 写入新的 squid.conf（端口: $PORT）"
sudo bash -c "cat > /etc/squid/squid.conf" <<EOF
http_port $PORT

auth_param basic program /usr/lib/squid/basic_ncsa_auth /etc/squid/passwd
auth_param basic realm Squid Proxy Authentication
acl authenticated proxy_auth REQUIRED
http_access allow authenticated

forwarded_for delete
request_header_access X-Forwarded-For deny all
request_header_access Via deny all
request_header_access Cache-Control deny all

http_access deny all

access_log /var/log/squid/access.log
cache_dir ufs /var/spool/squid 100 16 256
cache_mem 64 MB
request_body_max_size 10 MB
EOF

sudo chown proxy:proxy $PASSWD_FILE
sudo chmod 640 $PASSWD_FILE

echo "🔄 重启 Squid 服务..."
sudo systemctl restart squid

# 检查防火墙是否安装了 ufw
if command -v ufw > /dev/null; then
    echo "🌐 配置防火墙允许端口 $PORT ..."
    sudo ufw allow $PORT
    sudo ufw reload
else
    echo "⚠️ 未安装 ufw，跳过防火墙配置"
fi

# 显示结果
echo ""
echo "✅ Squid 已配置完成！"
echo "👉 代理服务器地址：$SERVER_IP:$PORT"
echo "👉 用户名：$USERNAME"
echo ""
echo "🧪 测试命令（替换 YOUR_PASSWORD）："
echo "curl -x http://$USERNAME:YOUR_PASSWORD@$SERVER_IP:$PORT http://example.com"
