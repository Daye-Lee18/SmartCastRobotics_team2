#!/usr/bin/env bash
set -euo pipefail

pytest server/main_service
pytest server/ai_service
pytest ui/pyqt/factory_operator
pytest device/smartcast_arm/control
pytest device/smartcast_amr/smartcast_amr_control
pytest device/camera

