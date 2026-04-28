#!/usr/bin/env python3
"""Jetson Image Publisher 배포 스크립트 (paramiko 기반, sshpass 불필요).

backend/management/venv 의 paramiko 를 사용. 사용자는 아래 환경변수 중 하나를 선택:
    MGMT_JETSON_SSH_KEY = /path/to/id_ed25519   (키 우선)
    또는
    MGMT_JETSON_PASS = <평문 비밀번호>           (.env.local 에 이미 설정됨)

사용:
    source backend/management/venv/bin/activate
    set -a && source backend/.env.local && set +a
    python3 jetson_publisher/deploy.py              # 코드만 재동기화
    python3 jetson_publisher/deploy.py --install    # systemd 유닛 + 의존성까지

동작:
    1) ~/casting-image-publisher/ 디렉터리 생성
    2) 로컬 jetson_publisher/ 내용을 SFTP 업로드 (__pycache__, deploy.py 제외)
    3) --install: env.example → env 복사, pip/apt 설치, systemd 등록
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

try:
    import paramiko
except ImportError:
    sys.exit("paramiko 미설치. `source backend/management/venv/bin/activate` 후 실행하세요.")


EXCLUDES = {"__pycache__", ".pyc", ".DS_Store", "deploy.py", "deploy.sh", ".venv"}


def _connect() -> paramiko.SSHClient:
    host = os.environ.get("MGMT_JETSON_HOST") or sys.exit("MGMT_JETSON_HOST 미설정")
    user = os.environ.get("MGMT_JETSON_USER") or sys.exit("MGMT_JETSON_USER 미설정")
    port = int(os.environ.get("MGMT_JETSON_PORT", "22"))
    key = os.environ.get("MGMT_JETSON_SSH_KEY")
    pw = os.environ.get("MGMT_JETSON_PASS")
    if not key and not pw:
        sys.exit("MGMT_JETSON_PASS 또는 MGMT_JETSON_SSH_KEY 중 하나 필요")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    kw = {"hostname": host, "port": port, "username": user, "timeout": 15}
    if key:
        kw["key_filename"] = key
    else:
        kw["password"] = pw
        kw["look_for_keys"] = False
        kw["allow_agent"] = False
    print(f">>> connecting {user}@{host}:{port} ({'key' if key else 'password'})")
    c.connect(**kw)
    return c


def _run(
    ssh: paramiko.SSHClient, cmd: str, check: bool = True, sudo_pw: str | None = None
) -> tuple[int, str, str]:
    print(f"    $ {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=300, get_pty=bool(sudo_pw))
    if sudo_pw:
        stdin.write(sudo_pw + "\n")
        stdin.flush()
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    rc = stdout.channel.recv_exit_status()
    if out.strip():
        for line in out.strip().splitlines():
            print(f"      {line}")
    if err.strip():
        for line in err.strip().splitlines():
            print(f"      ! {line}")
    if check and rc != 0:
        raise RuntimeError(f"remote cmd failed (rc={rc}): {cmd}")
    return rc, out, err


def _should_skip(name: str) -> bool:
    return any(ex in name for ex in EXCLUDES)


def _upload_dir(sftp: paramiko.SFTPClient, local: Path, remote: str) -> None:
    """디렉터리 재귀 업로드."""
    try:
        sftp.stat(remote)
    except OSError:
        sftp.mkdir(remote)
    for entry in sorted(local.iterdir()):
        if _should_skip(entry.name):
            continue
        rpath = f"{remote}/{entry.name}"
        if entry.is_dir():
            _upload_dir(sftp, entry, rpath)
        else:
            sftp.put(str(entry), rpath)
            if entry.suffix in (".sh", ".py") or entry.name == "env":
                sftp.chmod(rpath, 0o755)
            else:
                sftp.chmod(rpath, 0o644)
            print(f"    → {rpath}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--install", action="store_true", help="systemd 유닛 등록 + 의존성 설치 (최초 1회)"
    )
    ap.add_argument("--restart", action="store_true", help="배포 후 systemd 서비스 재시작")
    args = ap.parse_args()

    local_dir = Path(__file__).resolve().parent
    user = os.environ["MGMT_JETSON_USER"]
    remote_dir = f"/home/{user}/casting-image-publisher"

    ssh = _connect()
    try:
        _run(ssh, f"mkdir -p {remote_dir}")
        sftp = ssh.open_sftp()
        try:
            _upload_dir(sftp, local_dir, remote_dir)
        finally:
            sftp.close()
        print(f">>> code synced to {remote_dir}")

        if args.install:
            pw = os.environ.get("MGMT_JETSON_PASS")
            if not pw:
                print("!! --install 은 sudo 비밀번호 필요. MGMT_JETSON_PASS 설정 필요.")
                return 2
            sudo = f"echo '{pw}' | sudo -S"

            # env 파일 초기화 (최초만)
            _run(ssh, f"[ -f {remote_dir}/env ] || cp {remote_dir}/env.example {remote_dir}/env")

            # Python 의존성
            _run(
                ssh, f"python3 -m pip install --user -r {remote_dir}/requirements.txt", check=False
            )

            # OpenCV (apt 권장)
            _run(
                ssh,
                "python3 -c 'import cv2' 2>/dev/null && echo HAVE_CV2 || echo NEED_CV2",
                check=False,
            )
            print(">>> (cv2 미설치 시) sudo apt install python3-opencv — Jetson 측 수동 실행 권장")

            # systemd 유닛 등록
            _run(
                ssh,
                f"{sudo} cp {remote_dir}/systemd/casting-image-publisher.service "
                f"/etc/systemd/system/",
            )
            _run(ssh, f"{sudo} systemctl daemon-reload")
            _run(ssh, f"{sudo} systemctl enable casting-image-publisher.service", check=False)
            print(">>> systemd 유닛 등록 완료")
            print(">>> 다음 단계:")
            print(f"    1) ssh {user}@{os.environ['MGMT_JETSON_HOST']}")
            print("    2) nano ~/casting-image-publisher/env   # MANAGEMENT_GRPC_HOST 등 수정")
            print("    3) sudo apt install -y python3-opencv   # cv2 없을 때만")
            print("    4) sudo systemctl start casting-image-publisher")

        if args.restart:
            pw = os.environ.get("MGMT_JETSON_PASS", "")
            sudo = f"echo '{pw}' | sudo -S" if pw else "sudo"
            _run(ssh, f"{sudo} systemctl restart casting-image-publisher", check=False)
            _run(ssh, "systemctl is-active casting-image-publisher", check=False)

        return 0
    finally:
        ssh.close()


if __name__ == "__main__":
    sys.exit(main())
