import time
import json
import machine
import network

from umqtt.simple import MQTTClient

from Projeto_Sist_Embarcados.software.python.constantes import *
from Projeto_Sist_Embarcados.software.python.motores import *


current_throttle = 0
current_steering = 0
_print_counter = 0

def blink(n):
  for _ in range(n):
    LED.on(); time.sleep(0.2)
    LED.off(); time.sleep(0.2)

# ════════════════════════════════════════════════════════════════
#  Wi-Fi
# ════════════════════════════════════════════════════════════════
def connect_wifi():
  wlan = network.WLAN(network.STA_IF)
  wlan.active(False)
  wlan.active(True)
  if wlan.isconnected():
    return
  print(f"[WiFi] Conectando a {WIFI_SSID}...")
  wlan.connect(WIFI_SSID, WIFI_PASS)
  for _ in range(20):
    if wlan.isconnected():
      break
    time.sleep(0.8)
    print(".", end="")
  print()
  if wlan.isconnected():
    blink(3)   # 3 piscadas = Wi-Fi OK
    print(f"[WiFi] IP: {wlan.ifconfig()[0]}")
  else:
    print("[WiFi] Falha — reiniciando...")
    machine.reset()

# ════════════════════════════════════════════════════════════════
#  MQTT
# ════════════════════════════════════════════════════════════════
def on_message(topic, msg):
  global current_throttle, current_steering
  try:
    data = json.loads(msg.decode("utf-8"))
    
    thr = int(data.get("throttle", 0))
    ste = int(data.get("steering", 0))
    
    # Throttle: apenas positivo (sem ré)
    current_throttle = clamp(thr, 0, 100)
    current_steering = clamp(ste, -100, 100)
    
    aplicar_controles(current_throttle, current_steering)
    print(f"[MQTT] thr={current_throttle:3d}%  str={current_steering:+4d}°")
  
  except Exception as e:
    print(f"[MQTT] Payload inválido: {e}")


def connect_mqtt():
  print(f"[MQTT] Tentando {MQTT_HOST.decode()}:{MQTT_PORT}...")
  try:
    client = MQTTClient(MQTT_CLIENT, MQTT_HOST, port=MQTT_PORT, keepalive=60)
    client.set_callback(on_message)
    client.connect()
    client.subscribe(TOPIC_CTRL)
    print("[MQTT] Conectado!")
    blink(5)   # 5 piscadas = sucesso
    return client
  except Exception as e:
    print(f"[MQTT] Erro: {e}")
    raise


def publicar_velocidade(client):
  global current_throttle, _print_counter
  spd = ler_velocidade(current_throttle)
  client.publish(TOPIC_SPEED, json.dumps({"speed": spd}).encode())

  _print_counter += 1
  if _print_counter >= 20:  # imprime a cada 20 * 0.05s = 1s
    print(f"[SPEED] {spd} km/h  throttle={current_throttle}")
    _print_counter = 0


# ════════════════════════════════════════════════════════════════
#  Bateria
# ════════════════════════════════════════════════════════════════
def ler_bateria():
  """
  Lê a tensão da bateria via divisor de tensão no GPIO 13.
  Faz 8 leituras e tira a média para reduzir ruído do ADC.
  Retorna dict com tensão (V) e percentual (%).
  """
  global battery_v
  samples = [BATTERY_PIN.read() for _ in range(8)]
  raw = sum(samples) // len(samples)
  # Converte leitura ADC → tensão real na bateria
  v_pino  = (raw / 4095) * 3.3          # tensão no pino GPIO
  battery_v = round(v_pino * FATOR_DIVISOR, 2)   # tensão real da bateria
  pct = (battery_v - BAT_MIN) / (BAT_MAX - BAT_MIN) * 100
  pct = max(0, min(100, round(pct)))
  return {"voltage": battery_v, "percent": pct}

