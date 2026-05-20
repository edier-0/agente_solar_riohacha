#!/usr/bin/env bash
# server.sh – Arranca Streamlit + FastAPI en una sesión tmux unificada

SESSION="solar_ai_session"

# Si la sesión ya existe, la cerramos para reiniciar limpio
if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "⚠️ La sesión '$SESSION' ya existía → reiniciando de forma limpia..."
  tmux kill-session -t "$SESSION"
fi

# 1️⃣ Crear la sesión, activar entorno virtual y lanzar Streamlit en la primera ventana
# Usamos bash -c para asegurar que se active el entorno virtual de Python antes de correr el servicio
tmux new-session -d -s "$SESSION" -n "servicios" "bash -c 'source .venv/bin/activate && streamlit run Inicio.py'"

# 2️⃣ Dividir la pantalla verticalmente (lado derecho) para lanzar FastAPI
tmux split-window -h -t "$SESSION:servicios" "bash -c 'source .venv/bin/activate && uvicorn api.main:app --reload --port 8000'"

# (Opcional) Balancear los paneles para que midan 50% y 50% cada uno
tmux select-layout -t "$SESSION:servicios" even-horizontal

# 3️⃣ Adjuntar la sesión al terminal actual para que veas ambos logs en vivo
tmux attach-session -t "$SESSION"