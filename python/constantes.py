# ╔══════════════════════════════════════════════════════════════╗
# ║                      CONFIGURAÇÃO                            ║
# ╚══════════════════════════════════════════════════════════════╝

import machine
from Projeto_Sist_Embarcados.software.python.mpu6050 import accel as MPU6050

# Configurações de WiFi
WIFI_SSID   = "S24 de Gabriel"
WIFI_PASS   = "bahgonet01"

# Configurações de MQTT
MQTT_HOST   = b"10.157.252.188"
MQTT_PORT   = 1883
MQTT_CLIENT = b"esp32_rccar"

TOPIC_CTRL  = b"rccar/control"   # subscreve (recebe comandos)
TOPIC_SPEED = b"rccar/speed"     # publica (envia velocidade)
TOPIC_BATTERY = b"rccar/battery"  # publica tensão da bateria

SPEED_INTERVAL = 0.05             # segundos entre publicações

# ── Motor DC ─────────────────────────────────────────────────────
#    GPIO conectado à base do transistor / gate do MOSFET
#    PWM controla a velocidade (0 = parado, 1023 = máximo)
MOTOR_PIN = machine.PWM(machine.Pin(16), freq=1000)

# Duty mínimo para o motor TT vencer a inércia (~30–40%)
# Aumente se o motor não der partida em velocidades baixas
MOTOR_MIN_DUTY = 350   # de 1023
MOTOR_MAX_DUTY = 1023

# ── Servo (direção) ──────────────────────────────────────────────
#    50Hz (período 20ms)
#    Pulso: 1.0ms = esquerda | 1.5ms = centro | 2.0ms = direita
#    duty (0–1023):  1.0ms → 51 | 1.5ms → 77 | 2.0ms → 102
SERVO_PIN    = machine.PWM(machine.Pin(23), freq=50)
SERVO_CENTER = 77    # ajuste se o servo não centralizar
SERVO_LEFT   = 51    # ajuste conforme o ângulo máximo do seu servo
SERVO_RIGHT  = 102   # ajuste conforme o ângulo máximo do seu servo

# MPU6050
i2c = machine.I2C(0, scl=machine.Pin(22), sda=machine.Pin(21), freq=400000)
mpu = MPU6050(i2c)

# ── Bateria ───────────────────────────────────────────────────────
#  Divisor de tensão no GPIO 13:
#    Bateria (+) ──[R1=100kΩ]──┬──[R2=100kΩ]── GND
#                               └──► GPIO 13 (ADC)
#
#  Com R1=R2=100kΩ: tensão no pino = Vbat / 2
#  O ESP32 lê 0–3.3V → 0–4095 (ADC 12 bits)
#  Fórmula: Vbat = (leitura / 4095) * 3.3 * FATOR_DIVISOR
#
#  Ajuste BAT_MIN e BAT_MAX conforme o tipo da sua bateria:
#    LiPo 1S:  3.3V (vazia) … 4.2V (cheia)
#    LiPo 2S:  6.6V … 8.4V   → use R1=200kΩ, R2=100kΩ (÷3)
#    NiMH 4x:  4.8V … 5.6V
#    Li-ion 2S: igual ao LiPo 2S
BATTERY_PIN    = machine.ADC(machine.Pin(34))
BATTERY_PIN.atten(machine.ADC.ATTN_11DB)   # faixa 0–3.3V
#  Divisor ÷3 com R1=200kΩ e R2=100kΩ
#  V_pino = V_bat / 3  →  máx 8.4V / 3 = 2.8V (dentro dos 3.3V do ADC)
FATOR_DIVISOR  = 3.0    # R1=200kΩ, R2=100kΩ → divisor por 3
BAT_MIN        = 6.0    
BAT_MAX        = 7.4    
BATTERY_INTERVAL = 5.0  # segundos entre leituras de bateria

LED = machine.Pin(15, machine.Pin.OUT)