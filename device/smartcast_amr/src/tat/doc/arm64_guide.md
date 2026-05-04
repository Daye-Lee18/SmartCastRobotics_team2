# ARM64 PC ?�경 ?�정 가?�드
?�재 ?�키지�?arm64 ?�경?�서 ?�용?�려�??�래 과정???�요?�니??## PC ?�정

### 1. tat ROS2 pkg clone
```
mkdir -p ~/tat/src
cd ~/tat/src
git clone https://github.com/pinklab-art/tat.git
```
### 2. (Gazebo ?�용 ?? tat_gz_sim ?�키지??CMakeLists.txt ?�정
8-11 번째 �?부�???��?�거??주석 처리
```
if(CMAKE_SYSTEM_PROCESSOR STREQUAL "aarch64")
  message(StatUS "This package is skipped on aarch64.")
  return()
endif()
```
### 3. ?�드?�어 ?�서 관???�키지 ??��
```
cd ~/tat/src/tat
sudo rm -rf tat_emotion tat_imu_bno055 tat_lamp_control tat_led tat_sensor_adc
```
### 4. ?�존???�치 (Dependency)
```
cd ~/tat
rosdep install --from-paths src --ignore-src -r -y
```
### 5. 빌드 (Build)
```
cd ~/tat
colcon build
```