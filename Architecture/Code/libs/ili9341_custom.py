from machine import Pin, SPI
import framebuf
import time

# ILI9341 Commands
ILI9341_SWRESET = 0x01
ILI9341_SLPIN = 0x10
ILI9341_SLPOUT = 0x11
ILI9341_DISPON = 0x29
ILI9341_CASET = 0x2A
ILI9341_RASET = 0x2B
ILI9341_RAMWR = 0x2C
ILI9341_COLMOD = 0x3A
ILI9341_MADCTL = 0x36

class ILI9341(framebuf.FrameBuffer):
    def __init__(self, width, height, spi, cs, dc, rst, touch_spi=None, touch_cs=None, backlight=None):
        self.width = width
        self.height = height
        self.spi = spi
        self.cs = Pin(cs, Pin.OUT)
        self.dc = Pin(dc, Pin.OUT)
        self.rst = Pin(rst, Pin.OUT)
        self.backlight = Pin(backlight, Pin.OUT) if backlight else None


        self.touch_spi = touch_spi
        self.touch_cs = Pin(touch_cs, Pin.OUT) if touch_cs else None

        self.buffer = bytearray(self.width * self.height * 2)
        super().__init__(self.buffer, self.width, self.height, framebuf.RGB565)

        self.init_display()

        if self.backlight:
            self.backlight.value(1)

    def write_cmd(self, cmd):
        self.dc.value(0) 
        self.cs.value(0)
        self.spi.write(bytearray([cmd]))
        self.cs.value(1)

    def write_data(self, data):
        self.dc.value(1)  
        self.cs.value(0)
        self.spi.write(data)
        self.cs.value(1)

    def init_display(self):
        """Initialize the ILI9341 display."""
 
        self.rst.value(0)
        time.sleep_ms(50)
        self.rst.value(1)
        time.sleep_ms(50)

       
        self.write_cmd(ILI9341_SWRESET)
        time.sleep_ms(150)
        self.write_cmd(ILI9341_SLPOUT)
        time.sleep_ms(150)

        self.write_cmd(ILI9341_COLMOD)
        self.write_data(bytearray([0x55]))
        time.sleep_ms(10)

        self.write_cmd(ILI9341_MADCTL)
        self.write_data(bytearray([0x48]))  

        self.write_cmd(ILI9341_DISPON)  
        time.sleep_ms(100)

    def set_window(self, x0, y0, x1, y1):
        """Set the active drawing window."""
        self.write_cmd(ILI9341_CASET)  
        self.write_data(bytearray([0x00, x0, 0x00, x1]))

        self.write_cmd(ILI9341_RASET)
        self.write_data(bytearray([0x00, y0, 0x00, y1]))

        self.write_cmd(ILI9341_RAMWR)  

    def show(self):
        """Push the buffer to the display."""
        self.set_window(0, 0, self.width - 1, self.height - 1)
        self.write_data(self.buffer)

    def draw_pixel(self, x, y, color):
        """Draw a single pixel."""
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            return
        self.set_window(x, y, x, y)
        self.write_data(bytearray([(color >> 8) & 0xFF, color & 0xFF]))

    def draw_button(self, x, y, w, h, color, label, text_color):
        """Draw a button with text."""
        self.fill_rect(x, y, w, h, color)
        self.text(label, x + w // 4, y + h // 4, text_color)
        self.show()

    def draw_slider(self, x, y, w, h, value, color, bg_color):
        """Draw a slider."""
        self.fill_rect(x, y, w, h, bg_color)  
        slider_pos = int(value * w)
        self.fill_rect(x, y, slider_pos, h, color) 
        self.show()

    def handle_touch(self):
        """Detect and handle touch inputs."""
        if not self.touch_spi or not self.touch_cs:
            return None  
        self.touch_cs.value(0)
        self.touch_spi.write(bytearray([0xD0]))  
        data = self.touch_spi.read(2)
        self.touch_cs.value(1)
        x = ((data[0] << 8) | data[1]) >> 4  
        return x

    @staticmethod
    def color565(r, g, b):
        """Convert RGB888 to RGB565."""
        return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
