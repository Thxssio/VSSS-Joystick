from typing import List, Optional, Tuple, Union
import numpy as np
import pygame
import struct
import serial
import time
import pyudev


def find_stm32_port() -> str:
    """
    Find the STM32 serial port.
    
    Returns:
        str: The STM32 serial device path
        
    Raises:
        RuntimeError: If the STM32 device is not found
    """
    context = pyudev.Context()
    for device in context.list_devices(subsystem='tty'):
        if 'ID_VENDOR_ID' in device and 'ID_MODEL_ID' in device:
            vendor_id: str = device.get('ID_VENDOR_ID')
            model_id: str = device.get('ID_MODEL_ID')

            if vendor_id == '0483' and model_id == '5740':
                return device.device_node  

    raise RuntimeError("STM32 Virtual COM Port not found!")


class KeyboardControl:
    def __init__(self) -> None:
        """Initialize the keyboard control."""
        self.robot_id: int = 0  
        self.MAX_SPEED: float = 1.0  
        
        # Movement control variables
        self.vl: float = 0.0
        self.vr: float = 0.0
        self.forward: bool = False
        self.backward: bool = False
        self.left: bool = False
        self.right: bool = False
        
        # Screen setup for keyboard events capture
        self.screen: Optional[pygame.Surface] = None
        self.instruction_surfaces: List[pygame.Surface] = []
        self.instructions: List[str] = []
        
        # Connect to serial device
        try:
            self.ser: serial.Serial = serial.Serial(find_stm32_port(), 115200, timeout=1)
            print(f"✅ Connected to STM32 on port {self.ser.port}")
        except Exception as e:
            print(f"❌ Error connecting to STM32: {e}")
            raise

    def setup(self) -> None:
        """Initialize Pygame and set up the window."""
        pygame.init()
        # Create a small window to capture keyboard events
        self.screen = pygame.display.set_mode((400, 250))
        pygame.display.set_caption('Keyboard Control')
        
        # Add instruction text
        font: pygame.font.Font = pygame.font.Font(None, 24)
        self.instructions = [
            "Use arrow keys or WASD to move the robot",
            "W/Up: Forward, S/Down: Backward",
            "A/Left: Turn left, D/Right: Turn right",
            "Press X to change robot ID",
            "ESC to exit"
        ]
        self.instruction_surfaces = [font.render(instr, True, (255, 255, 255)) for instr in self.instructions]
        
        print("⌨️ Keyboard control initialized.")
        print("Use arrow keys or WASD to move, X to change robot ID, ESC to exit.")

    def send_data(self) -> None:
        """Send data via serial to the STM32."""
        try:
            data: bytes = struct.pack('iff', self.robot_id, self.vl, self.vr)
            self.ser.write(data)
            print(f"📤 Sent: ID={self.robot_id}, VL={self.vl:.2f}, VR={self.vr:.2f}")
        except Exception as e:
            print(f"❌ Error sending data: {e}")

    def update_velocities(self) -> None:
        """Update velocities based on pressed keys."""
        self.vl = 0.0
        self.vr = 0.0
        
        if self.forward:
            self.vl += self.MAX_SPEED
            self.vr += self.MAX_SPEED
        if self.backward:
            self.vl -= self.MAX_SPEED
            self.vr -= self.MAX_SPEED
        if self.left:
            self.vl -= self.MAX_SPEED/2
            self.vr += self.MAX_SPEED/2
        if self.right:
            self.vl += self.MAX_SPEED/2
            self.vr -= self.MAX_SPEED/2

    def process_input(self) -> bool:
        """
        Read and process keyboard events.
        
        Returns:
            bool: True if the program should continue running, False to exit
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
                
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                # Arrow keys
                elif event.key == pygame.K_UP:
                    self.forward = True
                elif event.key == pygame.K_DOWN:
                    self.backward = True
                elif event.key == pygame.K_LEFT:
                    self.left = True
                elif event.key == pygame.K_RIGHT:
                    self.right = True
                # WASD keys
                elif event.key == pygame.K_w:
                    self.forward = True
                elif event.key == pygame.K_s:
                    self.backward = True
                elif event.key == pygame.K_a:
                    self.left = True
                elif event.key == pygame.K_d:
                    self.right = True
                # Change robot ID
                elif event.key == pygame.K_x:
                    self.robot_id = (self.robot_id + 1) % 4
                    print(f"🚀 Robot ID changed to: {self.robot_id}")
                    
            elif event.type == pygame.KEYUP:
                # Arrow keys
                if event.key == pygame.K_UP:
                    self.forward = False
                elif event.key == pygame.K_DOWN:
                    self.backward = False
                elif event.key == pygame.K_LEFT:
                    self.left = False
                elif event.key == pygame.K_RIGHT:
                    self.right = False
                # WASD keys
                elif event.key == pygame.K_w:
                    self.forward = False
                elif event.key == pygame.K_s:
                    self.backward = False
                elif event.key == pygame.K_a:
                    self.left = False
                elif event.key == pygame.K_d:
                    self.right = False
        
        self.update_velocities()
        self.send_data()
        
        # Update screen with instructions
        if self.screen:
            self.screen.fill((0, 0, 0))
            y_pos: int = 20
            for surface in self.instruction_surfaces:
                self.screen.blit(surface, (20, y_pos))
                y_pos += 30
                
            # Show current robot ID
            font: pygame.font.Font = pygame.font.Font(None, 36)
            id_text: pygame.Surface = font.render(f"Robot ID: {self.robot_id}", True, (255, 255, 0))
            self.screen.blit(id_text, (20, y_pos + 10))
            
            # Show current velocities
            vel_text: pygame.Surface = font.render(f"VL: {self.vl:.2f}, VR: {self.vr:.2f}", True, (0, 255, 255))
            self.screen.blit(vel_text, (20, y_pos + 50))
            
            # Show active keys
            active_keys: List[str] = []
            if self.forward: active_keys.append("W/Up")
            if self.backward: active_keys.append("S/Down")
            if self.left: active_keys.append("A/Left")
            if self.right: active_keys.append("D/Right")
            
            if active_keys:
                key_text: pygame.Surface = font.render(f"Active keys: {', '.join(active_keys)}", True, (255, 128, 0))
                self.screen.blit(key_text, (20, y_pos + 90))
            
            pygame.display.flip()
        
        return True

    def run(self) -> None:
        """Main keyboard control loop."""
        try:
            running: bool = True
            while running:
                running = self.process_input()
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            pygame.quit()
            if hasattr(self, 'ser') and self.ser.is_open:
                self.ser.close()


if __name__ == "__main__":
    controller: KeyboardControl = KeyboardControl()
    controller.setup()
    controller.run()