@echo off
start "" "C:\Users\User\AppData\Local\Programs\Ollama\ollama.exe" serve
timeout /t 5 /nobreak >nul
start "" /min "C:\Users\User\Documents\Proyectos\ngrok.exe" http --domain=scabbed-uneven-habitant.ngrok-free.dev 11434