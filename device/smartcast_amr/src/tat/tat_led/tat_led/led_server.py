import rclpy
from rclpy.node import Node

from .tatled import LED 

from tat_interfaces.srv import SetLed, SetBrightness

class LedServiceServer(Node):
    def __init__(self):
        super().__init__('led_service_server')
        
        self.led = LED()

        self.led_service = self.create_service(SetLed, 'set_led', self.set_led_callback)
        self.brightness_service = self.create_service(SetBrightness, 'set_brightness', self.set_brightness_callback)
        self.get_logger().info('LED control service server is ready.')

    def set_led_callback(self, request, response):
        if self.led is None:
            response.success = False
            response.message = "LED object is not initialized."
            return response

        command = request.command.lower()
        color = (request.r, request.g, request.b)
        
        try:
            if command == 'set_pixel':
                for pixel in request.pixels:
                    self.led.set_pixel(pixel, color)
                
                self.led.show()
                response.success = True
                response.message = f"Set pixel(s) {request.pixels} to color {color}."
            
            elif command == 'fill':
                self.led.fill(color)
                response.success = True
                response.message = f"Filled all LEDs with color {color}."

            elif command == 'clear':
                self.led.clear()
                response.success = True
                response.message = "Cleared all LEDs."
            
            else:
                response.success = False
                response.message = f"Failed: Unknown command. Available commands: 'set_pixel', 'fill', 'clear'."

            self.get_logger().info(response.message)

        except IndexError as e:
            response.success = False
            response.message = f"Failed: {str(e)}"
            self.get_logger().error(response.message)
        except Exception as e:
            response.success = False
            response.message = f"Failed: Error during LED control - {str(e)}"
            self.get_logger().error(response.message)

        return response
   
    def set_brightness_callback(self, request, response):
        if self.led is None:
            response.success = False
            response.message = "LED object is not initialized."
            return response

        try:
            self.led.set_brightness(request.brightness)
            response.success = True
            response.message = f"Set LED brightness to {request.brightness}."
            self.get_logger().info(response.message)
        
        except (ValueError, Exception) as e:
            response.success = False
            response.message = f"Failed: Error during brightness control - {str(e)}"
            self.get_logger().error(response.message)
        return response


def main(args=None):
    rclpy.init(args=args)
    led_service_node = LedServiceServer()
    try:
        rclpy.spin(led_service_node)
    except KeyboardInterrupt:
        pass
    finally:
        led_service_node.led.clear()
        led_service_node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()