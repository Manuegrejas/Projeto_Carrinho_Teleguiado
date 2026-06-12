import time
from Projeto_Sist_Embarcados.software.python.constantes import *

speed_kmh = 0.0
current_throttle = 0
current_steering = 0
ax_offset = 0

def clamp(val, lo, hi):
  return max(lo, min(val, hi))

# ════════════════════════════════════════════════════════════════
#  Motor DC
# ════════════════════════════════════════════════════════════════
def set_motor(throttle_pct):
  """
  throttle_pct: 0 (parado) … 100 (máximo)
  Converte para PWM proporcional.
  Abaixo de 1% considera stop para evitar zumbido desnecessário.
  """
  if throttle_pct <= 0:
    MOTOR_PIN.duty(0)
  else:
    duty = int(MOTOR_MIN_DUTY + (MOTOR_MAX_DUTY - MOTOR_MIN_DUTY) * (throttle_pct / 100))
    MOTOR_PIN.duty(clamp(duty, MOTOR_MIN_DUTY, MOTOR_MAX_DUTY))


# ════════════════════════════════════════════════════════════════
#  Servo
# ════════════════════════════════════════════════════════════════
def set_servo(steering_pct):
  """
  steering_pct: -100 (esquerda máx) … 0 (centro) … +100 (direita máx)
  Direções invertidas em relação à montagem física do servo.
  """
  if steering_pct >= 0:
    # Centro → Esquerda (invertido)
    position = int(SERVO_CENTER - (steering_pct / 100) * (SERVO_CENTER - SERVO_LEFT))
  else:
    # Direita → Centro (invertido)
    position = int(SERVO_CENTER - (steering_pct / 100) * (SERVO_RIGHT - SERVO_CENTER))

  SERVO_PIN.duty(clamp(position, SERVO_LEFT, SERVO_RIGHT))



def aplicar_controles(current_throttle, current_steering):
  set_motor(current_throttle)
  set_servo(current_steering)


def parar_tudo():
  """Para o motor e centraliza o servo."""
  set_motor(0)
  set_servo(0)

def calibrar_acelerometro(amostras=200):
    global ax_offset
    soma = 0
    for _ in range(amostras):
        dados = mpu.get_values()
        soma += dados["AcX"]
        time.sleep(0.005)
    ax_offset = soma / amostras
    print(f"[MPU] Offset calibrado: AcX = {ax_offset:.1f}")


# ════════════════════════════════════════════════════════════════
def ler_velocidade(current_throttle):
    global speed_kmh
    dados = mpu.get_values()

    # Remove o offset (gravidade + bias do sensor)
    ax_raw = dados["AcX"] - ax_offset
    ax = ax_raw / 16384.0 * 9.81

    # Zona morta para ruído
    if abs(ax) < 0.3:
        ax = 0.0

    if current_throttle > 0:
        speed_kmh += ax * SPEED_INTERVAL * 3.6
    else:
        speed_kmh *= 0.85

    if speed_kmh < 0.2:
        speed_kmh = 0.0

    speed_kmh = clamp(speed_kmh, 0.0, 20.0)
    return round(speed_kmh, 1)