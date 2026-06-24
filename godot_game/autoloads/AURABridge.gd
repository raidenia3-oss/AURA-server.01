## AURABridge.gd — Autoload de conexión WebSocket entre Godot 4.x y AURA Core
## Se connecta a ws://localhost:9090, maneja reconexión automática cada 5s
## Emite señales globales para todo el juego.
##
## CONFIGURACIÓN EN project.godot:
##   [autoload]
##   AURABridge = "res://autoloads/AURABridge.gd"
##
## PROTOCOLO JSON:
##   AURA → Godot: {"event": "TELEMETRY_UPDATE", "payload": {...}}
##   Godot → AURA: {"event": "BUFF_GRANTED", "payload": {...}}

extends Node

# ═══════════════════════════════════════════════════════════════
# SEÑALES GLOBALES — cualquier nodo del juego puede conectarse
# ═══════════════════════════════════════════════════════════════

## Se emite cuando AURA Core envía un evento al juego
signal aura_event(type: String, payload: Dictionary)

## Se emite cuando se conecta/desconecta del servidor
signal aura_connection_changed(connected: bool)

## Se emite cuando se recibe telemetry
signal aura_telemetry(data: Dictionary)

## Se emite cuando AURA pide spawnear un enemigo
signal aura_enemy_spawn(enemies: Array)

## Se emite cuando un buff es concedido
signal aura_buff_granted(buff_data: Dictionary)

## Se emite cuando el jugador sube de nivel (AURA confirma)
signal aura_level_confirmed(level: int, stats: Dictionary)

# ═══════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════

## URL del servidor WebSocket de AURA Core
const AURA_WS_URL: String = "ws://localhost:9090"

## Intervalo de reconexión automática (segundos)
const RECONNECT_INTERVAL: float = 5.0

## Heartbeat interval (segundos) para mantener la conexión viva
const HEARTBEAT_INTERVAL: float = 10.0

# ═══════════════════════════════════════════════════════════════
# ESTADO INTERNO
# ═══════════════════════════════════════════════════════════════

## Socket WebSocket activo
var _ws: WebSocketPeer = null

## Estado actual de conexión
var connected: bool = false
var _reconnect_timer: float = 0.0
var _heartbeat_timer: float = 0.0
var _connecting: bool = false

## Cola de mensajes pendientes de enviar (cuando se reconecta)
var _pending_messages: Array[Dictionary] = []

## Última telemetría recibida
var last_telemetry: Dictionary = {}


# ═══════════════════════════════════════════════════════════════
# CICLO DE VIDA
# ═══════════════════════════════════════════════════════════════

func _ready() -> void:
	"""Se ejecuta al iniciar el autoload. Inicia la conexión."""
	print("[AURABridge] Inicializando conexión a AURA Core...")
	print("[AURABridge] URL: ", AURA_WS_URL)
	_ws = WebSocketPeer.new()
	_reconnect_timer = 0.0
	_heartbeat_timer = 0.0
	# No conectar inmediatamente, esperar al primer frame
	_reconnect_timer = 0.1


func _process(delta: float) -> void:
	"""Procesamiento principal cada frame."""
	if _ws == null:
		return

	# Actualizar el socket (necesario para Godot 4 WebSocketPeer)
	_ws.poll()

	var state = _ws.get_ready_state()

	match state:
		WebSocketPeer.STATE_CONNECTING:
			# Aún conectando, no hacer nada
			pass

		WebSocketPeer.STATE_OPEN:
			if not connected:
				_on_connected()

			# Procesar mensajes entrantes
			_process_incoming()

			# Enviar heartbeat periódicamente
			_heartbeat_timer += delta
			if _heartbeat_timer >= HEARTBEAT_INTERVAL:
				_heartbeat_timer = 0.0
				_send_heartbeat()

		WebSocketPeer.STATE_CLOSING:
			# Esperando cierre limpio
			pass

		WebSocketPeer.STATE_CLOSED:
			if connected:
				_on_disconnected()
			# Programar reconexión
			_reconnect_timer += delta
			if _reconnect_timer >= RECONNECT_INTERVAL:
				_reconnect_timer = 0.0
				_connect()

	# Manejar mensajes pendientes
	_flush_pending()


func _connect() -> void:
	"""Intenta establecer conexión WebSocket con AURA Core."""
	if _connecting:
		return

	_connecting = true
	_reconnect_timer = 0.0
	_heartbeat_timer = 0.0

	# Crear nueva conexión
	_ws = WebSocketPeer.new()
	var error = _ws.connect_to_url(AURA_WS_URL)
	if error != OK:
		printerr("[AURABridge] Error al conectar: ", error)
		_connecting = false
	else:
		print("[AURABridge] Intentando conectar a ", AURA_WS_URL)


func _on_connected() -> void:
	"""Callback cuando se establece la conexión."""
	connected = true
	_connecting = false
	print("[AURABridge] ✅ Conectado a AURA Core")
	aura_connection_changed.emit(true)

	# Enviar mensaje de handshake
	_send_raw({
		"event": "GAME_CONNECTED",
		"payload": {
			"client": "godot_4x",
			"version": "1.0",
			"timestamp": Time.get_unix_time_from_system()
		}
	})

	# Enviar mensajes pendientes
	_flush_pending()


func _on_disconnected() -> void:
	"""Callback cuando se pierde la conexión."""
	connected = false
	_connecting = false
	print("[AURABridge] ❌ Desconectado de AURA Core")
	aura_connection_changed.emit(false)


func _process_incoming() -> void:
	"""Procesa todos los mensajes disponibles del socket."""
	while _ws.get_available_packet_count() > 0:
		var raw = _ws.get_packet().get_string()
		if raw.is_empty():
			continue

		var error = null
		var data = null

		# Parsear JSON
		data = JSON.parse_string(raw)
		if data == null:
			printerr("[AURABridge] JSON inválido recibido: ", raw.substr(0, 100))
			continue

		var event_type = data.get("event", "")
		var payload = data.get("payload", {})

		print("[AURABridge] 📥 Evento recibido: ", event_type)

		# Emitir señal global para que cualquier nodo del juego procese el evento
		aura_event.emit(event_type, payload)

		# Manejar eventos predefinidos internamente
		match event_type:
			"TELEMETRY_UPDATE":
				last_telemetry = payload
				aura_telemetry.emit(payload)

			"ENEMY_SPAWN":
				var enemies = payload.get("enemies", [])
				aura_enemy_spawn.emit(enemies)

			"BUFF_GRANTED":
				aura_buff_granted.emit(payload)

			"PLAYER_LEVEL_CONFIRMED":
				aura_level_confirmed.emit(payload.get("level", 1), payload.get("stats", {}))

			"SYNC_COMPLETE":
				print("[AURABridge] ✅ Sincronización con AURA completada")

			_:
				# Eventos no predefinidos, solo reemitir
				pass


func _send_heartbeat() -> void:
	"""Envía un heartbeat para mantener la conexión viva."""
	_send_raw({
		"event": "HEARTBEAT",
		"payload": {
			"timestamp": Time.get_unix_time_from_system(),
			"uptime": Time.get_ticks_msec() / 1000.0
		}
	})


func _flush_pending() -> void:
	"""Envía mensajes acumulados cuando se reconecta."""
	if _pending_messages.is_empty():
		return

	while _pending_messages.size() > 0:
		var msg = _pending_messages.pop_front()
		_send_raw(msg)


# ═══════════════════════════════════════════════════════════════
# API PÚBLICA — métodos que el resto del juego puede llamar
# ═══════════════════════════════════════════════════════════════

## Envía un evento a AURA Core.
## Si no está conectado, se encola para enviar al reconectar.
func send_to_aura(event: String, data: Dictionary = {}) -> void:
	var message = {
		"event": event,
		"payload": data,
		"timestamp": Time.get_unix_time_from_system()
	}

	if connected and _ws and _ws.get_ready_state() == WebSocketPeer.STATE_OPEN:
		_send_raw(message)
	else:
		_pending_messages.append(message)
		print("[AURABridge] 📤 Mensaje encolado (offline): ", event)


## Consulta el estado de un nodo AURA/AME por su ID.
## Retorna una Dictionary con la información o un dict vacío si no está disponible.
func get_node_status(node_id: String) -> Dictionary:
	if last_telemetry.has("nodes"):
		var nodes = last_telemetry["nodes"]
		if nodes is Array:
			for node in nodes:
				if node.get("id", "") == node_id:
					return node
		elif nodes is Dictionary:
			return nodes.get(node_id, {})
	return {}


## Obtiene estadísticas del héroe desde AURA Core.
## Retorna null si AURA no está conectado.
func get_hero_stats() -> Variant:
	if not connected:
		return null

	# Las stats del héroe se sincronizan via GameState
	if last_telemetry.has("hero_stats"):
		return last_telemetry["hero_stats"]
	return null


## Retorna verdadero si está conectado a AURA Core.
func is_connected_to_aura() -> bool:
	return connected


## Fuerza una reconexión.
func force_reconnect() -> void:
	connected = false
	_connecting = false
	_ws = WebSocketPeer.new()
	_reconnect_timer = 0.0


## Envía datos del héroe a AURA para que los guarde.
func sync_hero_data(stats: Dictionary) -> void:
	send_to_aura("HERO_DATA_SYNC", {
		"stats": stats,
		"timestamp": Time.get_unix_time_from_system()
	})


## Notifica a AURA que el jugador ganó XP.
func report_xp_gain(amount: int, source: String) -> void:
	send_to_aura("XP_GAINED", {
		"amount": amount,
		"source": source,
		"timestamp": Time.get_unix_time_from_system()
	})


## Notifica a AURA que el jugador subió de nivel.
func report_level_up(new_level: int, stats: Dictionary) -> void:
	send_to_aura("PLAYER_LEVEL_UP", {
		"level": new_level,
		"stats": stats,
		"timestamp": Time.get_unix_time_from_system()
	})


## Notifica a AURA que se obtuvo un buff de un enemigo derrotado.
func report_buff_granted(buff_data: Dictionary) -> void:
	send_to_aura("BUFF_GRANTED", buff_data)


## Solicita a AURA que actualice la telemetría (pull request).
func request_telemetry() -> void:
	send_to_aura("REQUEST_TELEMETRY")


# ═══════════════════════════════════════════════════════════════
# UTILIDADES INTERNAS
# ═══════════════════════════════════════════════════════════════

func _send_raw(data: Dictionary) -> void:
	"""Envía un Dictionary como JSON string al socket."""
	if _ws and _ws.get_ready_state() == WebSocketPeer.STATE_OPEN:
		var json_str = JSON.stringify(data)
		_ws.send_text(json_str)