#!/usr/bin/env bash
# Management Service mTLS 자체 CA + cert 발급 (S-001).
#
# 사용:
#   bash backend/management/scripts/gen_certs.sh
#
# 산출물 (gitignored):
#   backend/management/certs/ca.{key,crt,srl}
#   backend/management/certs/server.{key,csr,crt}
#   backend/management/certs/client.{key,csr,crt}
#
# 환경 변수 override:
#   MGMT_TLS_DAYS=3650        cert 유효기간 (기본 10년)
#   MGMT_TLS_SERVER_CN=...    서버 CN (기본 localhost)
#   MGMT_TLS_SAN=...          서버 SAN (기본 DNS:localhost,IP:127.0.0.1,IP:0.0.0.0)
set -euo pipefail

CERT_DIR="$(cd "$(dirname "$0")/.." && pwd)/certs"
DAYS="${MGMT_TLS_DAYS:-3650}"
SERVER_CN="${MGMT_TLS_SERVER_CN:-localhost}"
SAN="${MGMT_TLS_SAN:-DNS:localhost,IP:127.0.0.1,IP:0.0.0.0}"

mkdir -p "$CERT_DIR"
cd "$CERT_DIR"

echo "==> Cert 출력 디렉터리: $CERT_DIR"
echo "==> 유효기간 ${DAYS}일, 서버 CN=${SERVER_CN}, SAN=${SAN}"

# 1) CA
echo "==> CA 생성"
openssl genrsa -out ca.key 4096 2>/dev/null
openssl req -x509 -new -nodes -key ca.key -sha256 -days "$DAYS" \
    -subj "/CN=Casting Factory Mgmt CA/O=SmartCast Robotics" \
    -out ca.crt 2>/dev/null

# 2) 서버
echo "==> Server cert 생성 (CN=${SERVER_CN})"
openssl genrsa -out server.key 4096 2>/dev/null
openssl req -new -key server.key \
    -subj "/CN=${SERVER_CN}/O=SmartCast Robotics" \
    -out server.csr 2>/dev/null
cat > server.ext <<EOF
subjectAltName=${SAN}
extendedKeyUsage=serverAuth
EOF
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
    -out server.crt -days "$DAYS" -sha256 \
    -extfile server.ext 2>/dev/null

# 3) 클라이언트 (PyQt 공용)
echo "==> Client cert 생성"
openssl genrsa -out client.key 4096 2>/dev/null
openssl req -new -key client.key \
    -subj "/CN=casting-pyqt-client/O=SmartCast Robotics" \
    -out client.csr 2>/dev/null
cat > client.ext <<EOF
extendedKeyUsage=clientAuth
EOF
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
    -out client.crt -days "$DAYS" -sha256 \
    -extfile client.ext 2>/dev/null

# 권한
chmod 600 ca.key server.key client.key
chmod 644 ca.crt server.crt client.crt

# 임시 파일 정리
rm -f server.csr server.ext client.csr client.ext

echo ""
echo "==> 발급 완료. 파일 목록:"
ls -la "$CERT_DIR" | grep -E "\.(key|crt)$"
echo ""
echo "==> 활성화 방법:"
echo "  서버:  MGMT_GRPC_TLS_ENABLED=1 python server.py"
echo "  PyQt:  MGMT_GRPC_TLS_ENABLED=1 python main.py"
echo "         + cert 경로 환경변수 (선택, 기본 backend/management/certs)"
echo "         MGMT_TLS_CA_PATH, MGMT_TLS_CLIENT_KEY, MGMT_TLS_CLIENT_CRT"
