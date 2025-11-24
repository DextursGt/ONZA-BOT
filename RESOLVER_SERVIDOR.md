# 🔧 Resolver Problemas en el Servidor

## Problema: Conflicto de Git con main.py

El servidor tiene cambios locales en `main.py` que bloquean el merge.

## Solución Rápida

Ejecuta estos comandos en el servidor:

```bash
cd /root/ONZA-BOT

# Opción 1: Guardar cambios locales (si los necesitas)
git stash

# Opción 2: O descartar cambios locales (si no los necesitas)
# git reset --hard HEAD

# Ahora hacer pull
git pull origin main

# Verificar que el script existe
ls -la actualizar_fortnite.sh

# Ejecutar el script
bash actualizar_fortnite.sh
```

## Si Prefieres Actualizar Solo Fortnite Sin Resolver el Conflicto

```bash
cd /root/ONZA-BOT

# Actualizar solo la carpeta fortnite/ sin tocar main.py
git fetch origin
git checkout origin/main -- fortnite/

# Verificar que fortnite existe
ls -la fortnite/

# Agregar cryptography a requirements.txt
grep -q "cryptography" requirements.txt || echo -e "\n# Encryption for Fortnite tokens\ncryptography==41.0.7" >> requirements.txt

# Instalar dependencia
source venv/bin/activate
pip install cryptography==41.0.7
deactivate

# Editar main.py manualmente para agregar Fortnite
nano main.py
# Busca: self.add_cog(SimpleTicketCommands(self))
# Agrega después las líneas de Fortnite

# Reiniciar
systemctl restart onza-bot
```

