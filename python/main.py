# ════════════════════════════════════════════════════════════════════════════════
#  RC Car ESP32 — MicroPython + MQTT 
#
#  Payload recebido do site (JSON a ~20 Hz):
#    { "throttle": <-100…100>, "steering": <-100…100> }
#      throttle > 0  → frente   | throttle < 0 → ré    | 0 → stop
#      steering > 0  → direita  | steering < 0 → esq   | 0 → centro
#
#  Os valores são contínuos: 50 = metade da velocidade/ângulo,
#  100 = máximo. O ESP32 converte para PWM (0–1023) linearmente.
#
#  Dependências (já inclusas no firmware MicroPython padrão):
#    • umqtt.simple
#    • machine, network, json, time
#
#  Opcional:
#    • mpu6050.py  →  https://github.com/adamjezek98/MPU6050-ESP8266-MicroPython
# ════════════════════════════════════════════════════════════════════════════════

import machine
import time
import gc

from Projeto_Sist_Embarcados.software.python.constantes import *
from Projeto_Sist_Embarcados.software.python.network_MQTT import *

# "Coleta" lixo de memória para liberar espaço antes de iniciar o programa
gc.collect()

# ── Estado global ────────────────────────────────────────────────
current_throttle = 0   # 0 … 100
current_steering = 0   # -100 … 100
speed_kmh        = 0.0
battery_v        = 0.0
last_battery_ms  = 0
last_ping_ms     = 0

_motor_safe = machine.Pin(26, machine.Pin.OUT)
_motor_safe.off()

# ════════════════════════════════════════════════════════════════
#  Loop principal
# ════════════════════════════════════════════════════════════════
def main():
  global last_battery_ms, last_ping_ms
  parar_tudo()
  connect_wifi()
  calibrar_acelerometro()
  
  client = None
  counter = 0
  while True:
    if client is None:
      try:
        client = connect_mqtt()
      except Exception as e:
        print(f"[MQTT] Falha: {e} — tentando em 3s...")
        time.sleep(3)
        continue
    
    try:
      client.check_msg()
      publicar_velocidade(client)
      
      # Publica bateria a cada BATTERY_INTERVAL segundos
      global last_battery_ms
      agora = time.ticks_ms()
      if time.ticks_diff(agora, last_battery_ms) >= int(BATTERY_INTERVAL * 1000):
        last_battery_ms = agora
        bat = ler_bateria()
        client.publish(TOPIC_BATTERY, json.dumps(bat).encode())
        print(f"[BAT] {bat['voltage']}V  {bat['percent']}%")
    
      
      if time.ticks_diff(agora, last_ping_ms) >= 20000:
        last_ping_ms = agora
        client.ping()
    
      counter += 1
      if counter % 100 == 0:
        gc.collect()
        print(f"[MEM] livre: {gc.mem_free()} bytes")
        
      if counter % 50 == 0:  # a cada ~2.5s
        try:
          client.ping()
        except Exception as e:
          raise e
    
    except Exception as e:
      print(f"[MQTT] Erro: {e} — reconectando...")
      try: client.disconnect()
      except: pass
      client = None
      parar_tudo()
      time.sleep(1)


if __name__ == "__main__":
  main()