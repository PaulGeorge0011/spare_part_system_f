#!/bin/bash
# ============================================================
# 生成自签名 SSL 证书（用于内网 HTTPS / iframe 嵌入场景）
# 使用方法：在项目根目录执行  bash ssl/generate-cert.sh
# 证书文件将生成在 ssl/ 目录下
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CERT_DIR="$SCRIPT_DIR"

# 证书有效期（天）
DAYS=3650

# 证书信息（可按需修改）
SUBJ="/C=CN/ST=Guangdong/L=Guangzhou/O=SparePartSystem/OU=IT/CN=spare-part-system"

echo "📜 正在生成自签名 SSL 证书..."
echo "   目录: $CERT_DIR"
echo "   有效期: $DAYS 天"

# 生成私钥和证书（含 SAN 支持 IP 访问）
openssl req -x509 -nodes -days $DAYS -newkey rsa:2048 \
  -keyout "$CERT_DIR/server.key" \
  -out "$CERT_DIR/server.crt" \
  -subj "$SUBJ" \
  -addext "subjectAltName=IP:172.24.69.125,IP:127.0.0.1,DNS:localhost"

if [ $? -eq 0 ]; then
  echo ""
  echo "✅ 证书生成成功！"
  echo "   证书: $CERT_DIR/server.crt"
  echo "   私钥: $CERT_DIR/server.key"
  echo ""
  echo "📌 下一步："
  echo "   1. 重启 nginx 容器:  docker compose restart nginx"
  echo "   2. 在白码 iframe 中使用:  https://172.24.69.125:8443/"
  echo "   3. 首次访问需在浏览器中信任该证书（自签名证书）"
else
  echo ""
  echo "❌ 证书生成失败，请检查 openssl 是否已安装"
  exit 1
fi
