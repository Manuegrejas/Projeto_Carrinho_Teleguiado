// ╔══════════════════════════════════════════════════════════════╗
// ║                      CONFIGURAÇÃO                            ║
// ╠══════════════════════════════════════════════════════════════╣
const BROKER_URL = 'ws://10.157.252.188:9001';
const TOPIC_CTRL  = 'rccar/control';   // publica  → ESP32
const TOPIC_SPEED   = 'rccar/speed';     // subscreve ← ESP32
const TOPIC_BATTERY = 'rccar/battery';   // subscreve ← ESP32
const MAX_SPEED   = 20;                // km/h máx no velocímetro
const PUBLISH_HZ  = 20;               // publicações por segundo
// ╚══════════════════════════════════════════════════════════════╝

// Payload publicado:
//   { "throttle": <0…100>, "steering": <-100…100> }
//   throttle: 0 = stop, 100 = máxima velocidade (apenas frente)
//   steering: -100 = esq, 0 = centro, +100 = direita

const connDot      = document.getElementById('conn-dot');
const statusTxt    = document.getElementById('status-text');
const actionLbl    = document.getElementById('action-label'); // elemento removido do DOM
const brokerLabel  = document.getElementById('broker-label'); // elemento removido do DOM
const speedoValEl  = document.getElementById('speedo-val');
const joystickEl   = document.getElementById('joystick');
const joyKnob      = document.getElementById('joy-knob');
const steerFill    = document.getElementById('steer-fill');
const steerValEl   = document.getElementById('steer-val');
const throttleEl   = document.getElementById('throttle');
const throttleFill = document.getElementById('throttle-fill');
const throttleKnob = document.getElementById('throttle-knob');
const throttleVal  = document.getElementById('throttle-val');

if (brokerLabel) { try { brokerLabel.textContent = new URL(BROKER_URL).host; } catch { brokerLabel.textContent = BROKER_URL; } }

// throttle: 0…100 (sem ré)   steering: -100…100
let throttle = 0, steering = 0, mqttClient = null;

// ── Velocímetro (apenas número) ──────────────────────────────
function setSpeedometer(kmh) {
  const v = Math.round(Math.max(0, Math.min(kmh, MAX_SPEED)));
  speedoValEl.textContent = v;
  // Pulsa a cor conforme velocidade
  const intensity = v / MAX_SPEED;
  speedoValEl.style.textShadow = `0 0 ${16 + intensity*24}px rgba(168,85,247,${0.6 + intensity*0.4}), 0 0 40px rgba(168,85,247,${0.2 + intensity*0.3})`;
}

// ── Joystick (apenas eixo X) ──────────────────────────────────
let joyActive = false, joyPid = null;

function joyUpdate(clientX) {
  const r        = joystickEl.getBoundingClientRect();
  const cx       = r.left + r.width / 2;
  const outerRad = r.width / 2;
  const knobRad  = outerRad * 0.18;
  const maxTravel = outerRad - knobRad;

  let dx = clientX - cx;
  if (Math.abs(dx) > maxTravel) dx = Math.sign(dx) * maxTravel;

  // Apenas eixo X — Y fica fixo no centro
  joyKnob.style.setProperty('--jx', dx.toFixed(1) + 'px');

  steering = Math.round((dx / maxTravel) * 100);
  updateSteerUI(steering);
}

function joyReset() {
  joyActive = false; joyPid = null;
  joyKnob.style.setProperty('--jx', '0px');
  joyKnob.classList.remove('active');
  steering = 0; updateSteerUI(0);
}

joystickEl.addEventListener('pointerdown', e => {
  e.preventDefault(); joyActive = true; joyPid = e.pointerId;
  joystickEl.setPointerCapture(e.pointerId);
  joyKnob.classList.add('active'); joyUpdate(e.clientX);
});
joystickEl.addEventListener('pointermove', e => {
  if (!joyActive || e.pointerId !== joyPid) return;
  e.preventDefault(); joyUpdate(e.clientX);
});
joystickEl.addEventListener('pointerup',     joyReset);
joystickEl.addEventListener('pointercancel', joyReset);

function updateSteerUI(val) {
  const halfW = Math.abs(val) / 2;
  if (val >= 0) { steerFill.style.left = '50%';          steerFill.style.width = halfW+'%'; }
  else          { steerFill.style.left = (50-halfW)+'%'; steerFill.style.width = halfW+'%'; }
  steerValEl.textContent = (val >= 0 ? '+' : '') + val + '°';
  updateActionLabel();
}

// ── Throttle slider (0–100%, apenas positivo) ─────────────────
let thrActive = false, thrPid = null;

function thrUpdate(clientY) {
  const r   = throttleEl.getBoundingClientRect();
  const pad = r.height * 0.10;
  const travel = r.height - pad * 2;
  const relY = Math.max(0, Math.min(clientY - r.top - pad, travel));
  // Topo = 100%, fundo = 0%
  throttle = Math.round(((travel - relY) / travel) * 100);
  updateThrottleUI(throttle);
}

function thrRelease() {
  thrActive = false; thrPid = null;
  throttle = 0; updateThrottleUI(0);
}

throttleEl.addEventListener('pointerdown', e => {
  e.preventDefault(); thrActive = true; thrPid = e.pointerId;
  throttleEl.setPointerCapture(e.pointerId); thrUpdate(e.clientY);
});
throttleEl.addEventListener('pointermove', e => {
  if (!thrActive || e.pointerId !== thrPid) return;
  e.preventDefault(); thrUpdate(e.clientY);
});
throttleEl.addEventListener('pointerup',     thrRelease);
throttleEl.addEventListener('pointercancel', thrRelease);

function updateThrottleUI(val) {
  // val: 0…100
  // Fill: cresce do fundo para cima
  throttleFill.style.height = val + '%';

  // Knob: bottom 10% (idle) → bottom ~80% (máx)
  const knobBottom = 10 + (val / 100) * 70;
  throttleKnob.style.bottom = knobBottom + '%';
  throttleKnob.textContent  = val + '%';
  throttleKnob.className    = 'throttle-knob' + (val > 0 ? ' active' : '');

  throttleVal.textContent = val > 0 ? '▲ ' + val + '%' : 'STOP';
  throttleVal.style.color = val > 0 ? 'var(--glow-g)' : 'var(--text-dim)';
  updateActionLabel();
}

function updateActionLabel() {
  const t = throttle > 0 ? `FWD ${throttle}%` : 'STOP';
  const s = steering !== 0 ? ` | ${steering > 0 ? '+' : ''}${steering}°` : '';
  if (actionLbl) actionLbl.textContent = t + s;
}

// ── Teclado ───────────────────────────────────────────────────
const keysDown = new Set();
document.addEventListener('keydown', e => {
  if (keysDown.has(e.key)) return; keysDown.add(e.key);
  if ([' ','ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].includes(e.key)) e.preventDefault();
  if (e.key === ' ') { throttle = 0; steering = 0; updateThrottleUI(0); updateSteerUI(0); }
});
document.addEventListener('keyup', e => {
  keysDown.delete(e.key);
  if (['ArrowUp','w','W','ArrowDown','s','S'].includes(e.key)) { throttle = 0; updateThrottleUI(0); }
  if (['ArrowLeft','a','A','ArrowRight','d','D'].includes(e.key)) { steering = 0; updateSteerUI(0); }
});
setInterval(() => {
  if (keysDown.has('ArrowUp')   ||keysDown.has('w')||keysDown.has('W')) { throttle=Math.min(100,throttle+10); updateThrottleUI(throttle); }
  if (keysDown.has('ArrowDown') ||keysDown.has('s')||keysDown.has('S')) { throttle=Math.max(0,  throttle-10); updateThrottleUI(throttle); }
  if (keysDown.has('ArrowLeft') ||keysDown.has('a')||keysDown.has('A')) { steering=Math.max(-100,steering-15); updateSteerUI(steering); }
  if (keysDown.has('ArrowRight')||keysDown.has('d')||keysDown.has('D')) { steering=Math.min(100, steering+15); updateSteerUI(steering); }
}, 80);

// ── Bateria ───────────────────────────────────────────────────
const batFill  = document.getElementById('bat-fill');
const batPct   = document.getElementById('bat-pct');
const batV     = document.getElementById('bat-v');
const batBadge = document.getElementById('battery-badge');

function updateBattery(voltage, percent) {
  // Barra: largura máx = 11px (de x=2 a x=13 dentro do SVG)
  const w = Math.round((percent / 100) * 11);
  batFill.setAttribute('width', w);

  // Cor conforme nível
  let color;
  if (percent > 50)      color = 'var(--glow-g)';   // roxo
  else if (percent > 20) color = 'var(--glow-y)';  // lavanda
  else                   color = 'var(--glow-r)'; // rosa

  batFill.setAttribute('fill', color);
  batPct.style.color = color;
  batV.style.color   = color;

  batPct.textContent = percent + '%';
  batV.textContent   = voltage.toFixed(2) + 'V';
}

// ── MQTT ──────────────────────────────────────────────────────
function connectMQTT() {
  setStatus('CONECTANDO…', false);
  const client = mqtt.connect(BROKER_URL, {
    clientId: 'rccar_web_' + Math.random().toString(16).slice(2,8),
    keepalive: 30, reconnectPeriod: 3000, connectTimeout: 5000,
  });
  client.on('connect',   () => { setStatus('ONLINE', true); client.subscribe(TOPIC_SPEED, {qos:0}); client.subscribe(TOPIC_BATTERY, {qos:0}); });
  client.on('reconnect', () => setStatus('RECONECTANDO…', false));
  client.on('offline',   () => setStatus('OFFLINE', false));
  client.on('error', err => { console.error(err); setStatus('ERRO', false); });
  client.on('message', (topic, msg) => {
    if (topic === TOPIC_SPEED) {
      try { const d = JSON.parse(msg.toString()); setSpeedometer(parseFloat(d.speed) || 0); } catch {}
    } else if (topic === TOPIC_BATTERY) {
      try { const d = JSON.parse(msg.toString()); updateBattery(parseFloat(d.voltage)||0, parseFloat(d.percent)||0); } catch {}
    }
  });
  mqttClient = client;
}

function publish(payload) {
  if (!mqttClient?.connected) return;
  mqttClient.publish(TOPIC_CTRL, JSON.stringify(payload), {qos:0, retain:false});
}

function setStatus(text, online) {
  statusTxt.textContent = text;
  statusTxt.classList.toggle('on', online);
  connDot.classList.toggle('on', online);
}

setInterval(() => publish({ throttle, steering }), Math.round(1000 / PUBLISH_HZ));

updateThrottleUI(0); updateSteerUI(0);
connectMQTT();
