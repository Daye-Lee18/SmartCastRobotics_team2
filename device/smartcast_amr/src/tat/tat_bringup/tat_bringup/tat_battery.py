import smbus2
import time

class Battery:
    DEFAULT_I2C_BUS = 1
    DEFAULT_I2C_ADDRESS = 0x08

    REG_BATTERY = 0xF8

    def __init__(self, i2c_bus=DEFAULT_I2C_BUS, i2c_address=DEFAULT_I2C_ADDRESS, wait_time=0.001):
        self.i2c_address = i2c_address
        self.bus = None
        self.wait_time = wait_time
        try:
            self.bus = smbus2.SMBus(i2c_bus)
        except FileNotFoundError:
            print(f"Error: I2C 버스 {i2c_bus}를 찾을 수 없습니다.")
            print("I2C가 활성화되어 있는지 확인하세요")
            raise

    def _read_adc_channel(self, register_cmd):
        if not self.bus:
            raise IOError("I2C 버스가 초기화되지 않았습니다.")
        
        try:
            self.bus.write_byte(self.i2c_address, register_cmd)
            time.sleep(self.wait_time) # ADC 변환 대기
            data = self.bus.read_i2c_block_data(self.i2c_address, 0, 2)
            return (data[0] << 4) | (data[1] >> 4)
        except OSError as e:
            print(f"I2C 통신 오류 (주소: 0x{self.i2c_address:02x}): {e}")
            return None

    def get_voltage(self):
        readings = []
        for _ in range(20):  # 10번 읽기
            adc_val = self._read_adc_channel(self.REG_BATTERY)
            if adc_val is not None:
                readings.append(adc_val)
    
        if not readings:  # 유효한 값이 하나도 없으면 None 반환
            return None
    
        avg_adc_val = sum(readings) / len(readings)
    
        voltage_divider_ratio = (13.0 / 28.0)
        voltage = (avg_adc_val / 4096.0) * 4.096 / voltage_divider_ratio
        return voltage

    def battery_percentage(self):
        full_voltage = 7.6   # 100%
        empty_voltage = 6.8  # 0%

        voltage = self.get_voltage()

        percent = (voltage - empty_voltage) / (full_voltage - empty_voltage) * 100
        percent = max(0, min(100, percent))  # 0~100% 제한
        return round(percent, 2)

    def close(self):
        if self.bus:
            self.bus.close()