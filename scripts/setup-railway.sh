#!/bin/bash

# Script para configurar Railway y desplegar el backend

# Variables
PROJECT_NAME="aura-backend"
RAILWAY_TOKEN="tu_token_railway"  # Reemplazar con token real
BACKEND_DIR="backend"

# Crear servicio de PostgreSQL en Railway
echo "Creando servicio de PostgreSQL en Railway..."
POSTGRES_SERVICE=$(railway create postgres --name aura-postgres --region la --addon)

# Obtener la URL de la base de datos
DATABASE_URL=$(railway get $POSTGRES_SERVICE --json | jq -r '.addonConfig.connectionString')

# Actualizar .env con la URL de la base de datos
echo "Actualizando DATABASE_URL en .env..."
echo "DATABASE_URL=$DATABASE_URL" > $BACKEND_DIR/.env
echo "QWEN_ENDPOINT=https://raiden456-slut.hf.space" >> $BACKEND_DIR/.env
echo "HF_TOKEN=tu_token_hf" >> $BACKEND_DIR/.env

# Desplegar el backend a Railway
echo "Desplegando backend a Railway..."
railway init $PROJECT_NAME --build-command="pip install -r $BACKEND_DIR/requirements.txt" --start-command="uvicorn $BACKEND_DIR.main:app --host 0.0.0.0 --port $PORT" --region la

# Obtener la URL del backend
BACKEND_URL=$(railway get $PROJECT_NAME --json | jq -r '.deployments[0].url')

# Actualizar el workflow N8N con la URL del backend
echo "Actualizando workflow N8N con la URL del backend..."
sed -i "s|https://app-xxx.railway.app|$BACKEND_URL|g" n8n/aura_news_workflow.json

echo "Configuración de Railway completada."
echo "Backend URL: $BACKEND_URL"
echo "PostgreSQL URL: $DATABASE_URL"