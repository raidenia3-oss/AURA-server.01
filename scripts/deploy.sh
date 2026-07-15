#!/bin/bash

# Script para desplegar todo el sistema AURA

echo "🚀 Iniciando despliegue completo de AURA..."

# Desplegar backend en Railway
echo "1. Desplegando backend en Railway..."
bash scripts/setup-railway.sh

# Obtener la URL del backend
BACKEND_URL=$(railway domain)

# Desplegar frontend en Vercel
echo "2. Desplegando frontend en Vercel..."
export BACKEND_URL=$BACKEND_URL
bash scripts/setup-vercel.sh

# Configurar N8N
echo "3. Configurando N8N..."
export DATABASE_URL=$(railway variables get DATABASE_URL)
bash scripts/setup-n8n.sh

echo "✅ Despliegue completado."
echo "Backend: $BACKEND_URL"
echo "Frontend: https://aura-frontend.vercel.app"
echo "N8N: https://n8n-onme.onrender.com"