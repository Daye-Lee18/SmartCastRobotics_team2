import os
import sys

if os.geteuid() != 0:
    ros_setup = "/opt/ros/jazzy/setup.bash"
    ws_setup = "~/tat/install/setup.bash"
    fastdds_xml = "~/.fastdds.xml"
    domain_id = os.environ.get('ROS_DOMAIN_ID', '0')
    
    cmd = f'sudo bash -c "export FASTRTPS_DEFAULT_PROFILES_FILE={fastdds_xml} && export ROS_DOMAIN_ID={domain_id} && source {ros_setup} && source {ws_setup} && {sys.executable} {" ".join(sys.argv)}"'
    
    os.system(cmd)
    sys.exit()

import time
from rpi_ws281x import PixelStrip, Color

if 'strip' in globals():
    try:
        strip._cleanup()
        time.sleep(0.1)
    except:
        pass

class LED:
    def __init__(self, num=8, pin=19, freq_hz=800000, dma=10, invert=False,
                 brightness=255, channel=1, strip_type=None, gamma=None):
        """
        Args:
            num (int): LED 픽셀의 총 개수
            pin (int): Raspberry Pi의 GPIO 핀 번호
            freq_hz (int): LED 신호 주파수 (보통 800000)
            dma (int): DMA 채널
            invert (bool): 신호 반전 여부
            brightness (int or float): LED 밝기 (0-255 정수 또는 0.0-1.0 실수)
            channel (int): PWM 채널
            strip_type: 스트립 타입
        """
        if isinstance(brightness, float) and 0.0 <= brightness <= 1.0:
            int_brightness = int(brightness * 255)
        elif isinstance(brightness, int) and 0 <= brightness <= 255:
            int_brightness = brightness
        else:
            raise ValueError("밝기(brightness)는 0.0-1.0 사이의 실수 또는 0-255 사이의 정수여야 합니다.")

        self._strip = PixelStrip(num, pin, freq_hz, dma, invert, int_brightness, channel, strip_type, gamma)
        
        self._strip.begin()
        self.count = num

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.clear()
        self._strip._cleanup()
        
    def show(self):
        self._strip.show()

    def clear(self):
        black = Color(0, 0, 0)
        for i in range(self.count):
            self._strip.setPixelColor(i, black)
        self.show()
    
    def set_pixel(self, index, color):
        """
        특정 인덱스의 픽셀 색상을 (R, G, B) 튜플로 설정합니다.

        Args:
            index (int): 색상을 변경할 픽셀의 인덱스 (0부터 시작)
            color (tuple): (R, G, B) 형태의 튜플. 각 값은 0-255.
        """
        if not (0 <= index < self.count):
            raise IndexError(f"픽셀 인덱스({index})가 범위를 벗어났습니다. (0-{self.count-1})")
        
        r, g, b = color
        self._strip.setPixelColor(index, Color(r, g, b))

    def set_brightness(self, brightness):
        """
        Args:
            brightness (int): 새로운 밝기 값 (0-255 정수)
        """
        if isinstance(brightness, float) and 0.0 <= brightness <= 1.0:
            int_brightness = int(brightness * 255)
        elif isinstance(brightness, int) and 0 <= brightness <= 255:
            int_brightness = brightness
        else:
            raise ValueError("밝기(brightness)는 0-255 사이의 정수여야 합니다.")
        
        self._strip.setBrightness(int_brightness)
        self.show()

    def get_brightness(self):
        """
        Returns:
            int: 현재 밝기 값 (0-255)
        """
        return self._strip.getBrightness()

    def get_pixel_color(self, index):
        """
        Args:
            index (int): 색상을 가져올 픽셀의 인덱스

        Returns:
            tuple: (R, G, B) 형태의 색상 튜플
        """
        if not (0 <= index < self.count):
            raise IndexError(f"픽셀 인덱스({index})가 범위를 벗어났습니다. (0-{self.count-1})")
        
        color_int = self._strip.getPixelColor(index)
        r = (color_int >> 16) & 0xFF
        g = (color_int >> 8) & 0xFF
        b = color_int & 0xFF
        return (r, g, b)

    def fill(self, color):
        r, g, b = color
        c = Color(r, g, b)
        for i in range(self.count):
            self._strip.setPixelColor(i, c)
        self.show()

    def numPixels(self):
        return self.count

    def _wheel(self, pos):
        if pos < 85:
            return Color(pos * 3, 255 - pos * 3, 0)
        elif pos < 170:
            pos -= 85
            return Color(255 - pos * 3, 0, pos * 3)
        else:
            pos -= 170
            return Color(0, pos * 3, 255 - pos * 3)

    def color_wipe(self, color, wait_ms=50):
        r, g, b = color
        c = Color(r, g, b)
        for i in range(self.count):
            self._strip.setPixelColor(i, c)
            self.show()
            time.sleep(wait_ms / 1000.0)

    def theater_chase(self, color, wait_ms=50, iterations=10):
        r, g, b = color
        c = Color(r, g, b)
        for j in range(iterations):
            for q in range(3):
                for i in range(0, self.count, 3):
                    if i + q < self.count:
                        self._strip.setPixelColor(i + q, c)
                self.show()
                time.sleep(wait_ms / 1000.0)
                for i in range(0, self.count, 3):
                    if i + q < self.count:
                        self._strip.setPixelColor(i + q, 0)

    def rainbow(self, wait_ms=20, iterations=1):
        for j in range(256 * iterations):
            for i in range(self.count):
                self._strip.setPixelColor(i, self._wheel((i + j) & 255))
            self.show()
            time.sleep(wait_ms / 1000.0)

    def rainbowCycle(self, wait_ms=20, iterations=5):
        for j in range(256 * iterations):
            for i in range(self.count):
                color = self._wheel((int(i * 256 / self.count) + j) & 255)
                self._strip.setPixelColor(i, color)
            self.show()
            time.sleep(wait_ms / 1000.0)

    def theaterChaseRainbow(self, wait_ms=50):
        for j in range(256):
            for q in range(3):
                for i in range(0, self.count, 3):
                    color = self._wheel((i + j) % 255)
                    if i + q < self.count:
                        self._strip.setPixelColor(i + q, color)
                self.show()
                time.sleep(wait_ms / 1000.0)
                for i in range(0, self.count, 3):
                    if i + q < self.count:
                        self._strip.setPixelColor(i + q, 0)

    def close(self):
        self.clear()
        self._strip._cleanup()
