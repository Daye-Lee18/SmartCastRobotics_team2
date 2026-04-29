# Jetson Image Publisher (V6 Image Publishing Service)

Jetson Orin NX 16GB 에서 USB 카메라 프레임을 Management Server(:50051) 로 gRPC client streaming 으로 push 한다.

## 구조

```
jetson_publisher/
├── publisher.py                 # 메인 실행 파일
├── requirements.txt             # grpcio / protobuf / numpy
├── env.example                  # 환경변수 템플릿
├── generated/                   # protoc 산출물 (monitoring/ 에서 복사)
│   ├── management_pb2.py
│   └── management_pb2_grpc.py
├── systemd/
│   └── casting-image-publisher.service
├── deploy.sh                    # 로컬 Mac → Jetson rsync
└── README.md
```

## 배포 (로컬 Mac → Jetson)

1회 설치:
```bash
bash jetson_publisher/deploy.sh --install
# → /home/jetson/casting-image-publisher/ 로 rsync + apt python3-opencv + systemd enable
```

이후 코드 변경만 동기화:
```bash
bash jetson_publisher/deploy.sh
ssh jetson@100.77.62.67 'sudo systemctl restart casting-image-publisher'
```

## Jetson 측 설정

```bash
# 1회만 — env 파일 수정
ssh jetson@100.77.62.67
cd ~/casting-image-publisher
nano env
#   MANAGEMENT_GRPC_HOST=<Mgmt Server Tailscale IP>
#   JETSON_CAMERA_ID=CAM-INSP-01 (또는 원하는 ID)

sudo systemctl start casting-image-publisher
sudo journalctl -u casting-image-publisher -f
```

## proto 재생성 시 (★ Jetson 호환성 주의)

Jetson (JetPack R35.5 / Python 3.8 / aarch64) 은 다음 런타임만 지원:
- `grpcio == 1.59.5` (aarch64 Python 3.8 최신 wheel)
- `protobuf 4.x` 또는 `protobuf 5.29.x` (5.x 는 업그레이드 후)

**protoc 산출물은 반드시 `grpcio-tools 1.59.x` 로 생성**해야 함. 최신(1.69+) 은 gencode 에
`_GRPC_VERSION >= "1.69.0"` 검증이 포함되어 Jetson 에서 import 실패.

```bash
# 1) 재생성 전용 venv (1회만)
python3.12 -m venv /tmp/protogen_venv
/tmp/protogen_venv/bin/pip install 'setuptools<81' 'grpcio-tools==1.59.3' 'protobuf>=4.21.6,<5'

# 2) 산출물 생성
rm -f /tmp/pbout/* && mkdir -p /tmp/pbout
cd backend/management
/tmp/protogen_venv/bin/python -m grpc_tools.protoc -I proto \
  --python_out=/tmp/pbout --grpc_python_out=/tmp/pbout proto/management.proto

# 3) relative import 패치
sed -i '' 's/^import management_pb2 as management__pb2/from . import management_pb2 as management__pb2/' \
  /tmp/pbout/management_pb2_grpc.py

# 4) jetson_publisher/ 로 복사 + 재배포
cp /tmp/pbout/management_pb2.py /tmp/pbout/management_pb2_grpc.py \
  jetson_publisher/generated/
python3 jetson_publisher/deploy.py --restart
```

재생성된 산출물 검증: 파일 상단에 `runtime_version` import 가 있더라도 ValidateProtobufRuntimeVersion 호출의 major 가 `4` 또는 `5` 여야 함 (6이면 Jetson 실패).

## 로컬 Mac 테스트 (E2E용 FaceTime/USB 웹캠)

```bash
cd jetson_publisher
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt opencv-python
export MANAGEMENT_GRPC_HOST=127.0.0.1
export JETSON_CAMERA_ID=CAM-INSP-MAC
python3 publisher.py
```

Management Server(:50051) 가 기동 중이어야 하며, `image_sink.stats()` 로 수신 확인 가능.
