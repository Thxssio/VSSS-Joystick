import numpy as np
import pygame
import struct
import serial
import time
import pyudev


def find_stm32_port():
    context = pyudev.Context()
    for device in context.list_devices(subsystem='tty'):
        if 'ID_VENDOR_ID' in device and 'ID_MODEL_ID' in device:
            vendor_id = device.get('ID_VENDOR_ID')
            model_id = device.get('ID_MODEL_ID')


            if vendor_id == '0483' and model_id == '5740':
                return device.device_node  

    raise RuntimeError("STM32 Virtual COM Port não encontrado!")


class JoystickControl:
    def __init__(self):
        """Inicializa o controle do joystick."""
        self.robot_id = 0  
        self.joystick = None
        self.axis = {}
        self.last_x_button_state = False  

        self.AXIS_LEFT_STICK_X = 0  
        self.AXIS_LEFT_STICK_Y = 1  
        self.BUTTON_X = 0  
        self.MAX_SPEED = 1.0  
        self.ser = serial.Serial(find_stm32_port(), 115200, timeout=1)

        print(f"✅ Conectado ao STM32 na porta {self.ser.port}")

    def setup(self):
        """Inicializa o Pygame e configura o joystick."""
        pygame.init()
        pygame.joystick.init()

        if pygame.joystick.get_count() < 1:
            raise RuntimeError("Nenhum joystick conectado.")

        self.joystick = pygame.joystick.Joystick(0)
        self.joystick.init()
        print(f"🎮 Joystick '{self.joystick.get_name()}' conectado.")

    def send_data(self, vl, vr):
        """Envia os dados via serial para o STM32."""
        try:
            data = struct.pack('iff', self.robot_id, vl, vr)
            self.ser.write(data)
            print(f"📤 Enviado: ID={self.robot_id}, VL={vl:.2f}, VR={vr:.2f}")
        except Exception as e:
            print(f"❌ Erro ao enviar dados: {e}")

    def process_input(self):
        """Lê e processa eventos do joystick."""
        pygame.event.pump() 

        y = -self.joystick.get_axis(self.AXIS_LEFT_STICK_Y)  
        x = self.joystick.get_axis(self.AXIS_LEFT_STICK_X)   

        if abs(y) < 0.1:
            y = 0
        if abs(x) < 0.1:
            x = 0


        vl = (y + x) * self.MAX_SPEED  
        vr = (y - x) * self.MAX_SPEED  

        x_button_state = self.joystick.get_button(self.BUTTON_X)
        if x_button_state and not self.last_x_button_state:
            self.robot_id = (self.robot_id + 1) % 4 
            print(f"🚀 Robô alterado para ID: {self.robot_id}")

        self.last_x_button_state = x_button_state 

        self.send_data(vl, vr)  

    def run(self):
        """Loop principal do controle do joystick."""
        try:
            while True:
                self.process_input()
        except KeyboardInterrupt:
            print("\nFinalizando...")
        finally:
            pygame.quit()
            self.ser.close()

if __name__ == "__main__":
    joystick = JoystickControl()
    joystick.setup()
    joystick.run()
