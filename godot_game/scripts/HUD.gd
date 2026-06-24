## HUD.gd — Interfaz del juego: XP, nivel, gold, buffs, log de eventos de AURA
## Se actualiza con señales de GameState y AURABridge

extends CanvasLayer

@onready var xp_bar: ProgressBar = $XPBar
@onready var level_label: Label = $LevelLabel
@onready var gold_label: Label = $GoldLabel
@onready var buff_label: Label = $BuffsLabel
@onready var log_text: RichTextLabel = $LogContainer/LogText
@onready var status_dot: ColorRect = $StatusDot

const MAX_LOG_LINES := 8

func _ready() -> void:
	GameState.xp_changed.connect(_on_xp_changed)
	GameState.level_changed.connect(_on_level_changed)
	GameState.gold_changed.connect(_on_gold_changed)
	GameState.buff_applied.connect(_on_buff_applied)
	AURABridge.aura_connection_changed.connect(_on_aura_connected)
	AURABridge.aura_event.connect(_on_aura_event)
	_refresh_all()
	add_log("[AURA] Conectando al servidor...")
	print("[HUD] Inicializado")

func _process(_delta: float) -> void:
	_update_buff_display()

func _refresh_all() -> void:
	xp_bar.max_value = GameState.xp_to_next
	xp_bar.value = GameState.xp
	level_label.text = "NV %d" % GameState.level
	gold_label.text = "%d Gold" % GameState.gold
	_update_buff_display()

func _on_xp_changed(_amount: int) -> void:
	xp_bar.max_value = GameState.xp_to_next
	xp_bar.value = GameState.xp

func _on_level_changed(new_level: int) -> void:
	level_label.text = "NV %d" % new_level
	add_log("¡LEVEL UP! Nivel %d" % new_level)

func _on_gold_changed(amount: int) -> void:
	gold_label.text = "%d Gold" % amount

func _on_buff_applied(buff: Dictionary) -> void:
	var tipo = buff.get("type", "?")
	var val = buff.get("value", 0)
	add_log("Buff: %s +%.1f" % [tipo, val])

func _on_aura_connected(connected: bool) -> void:
	status_dot.color = Color.GREEN if connected else Color.RED
	add_log("[AURA] %s" % ("Conectado" if connected else "Desconectado"))

func _on_aura_event(event_type: String, payload: Dictionary) -> void:
	add_log("AURA → %s: %s" % [event_type, str(payload).substr(0, 60)])

func add_log(message: String) -> void:
	if not log_text:
		return
	var timestamp = Time.get_datetime_string_from_system().substr(11, 8)
	var line = "[%s] %s" % [timestamp, message]
	if log_text.get_line_count() >= MAX_LOG_LINES:
		log_text.clear()
	log_text.append_text(line + "\n")

func _update_buff_display() -> void:
	var parts = []
	for buff in GameState.active_buffs:
		parts.append("%s (%ds)" % [buff.type, int(buff.remaining)])
	buff_label.text = "Buffs: " + (", ".join(parts) if parts.size() > 0 else "ninguno")