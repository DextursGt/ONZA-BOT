#!/usr/bin/env python3
"""
Script para convertir todos los comandos de guild a globales
"""

import os
import re

def fix_commands_in_file(file_path):
    """Arreglar comandos en un archivo específico"""
    print(f"🔧 Procesando {file_path}...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Reemplazar guild_ids=[GUILD_ID] if GUILD_ID else None con nada
    old_pattern = r', guild_ids=\[GUILD_ID\] if GUILD_ID else None'
    new_content = re.sub(old_pattern, '', content)
    
    if new_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"✅ {file_path} actualizado")
        return True
    else:
        print(f"ℹ️ {file_path} no necesita cambios")
        return False

def main():
    """Función principal"""
    commands_dir = "commands"
    files_to_fix = [
        "reviews.py",
        "moderation.py", 
        "tickets.py",
        "publication.py",
        "user.py"
    ]
    
    total_fixed = 0
    for filename in files_to_fix:
        file_path = os.path.join(commands_dir, filename)
        if os.path.exists(file_path):
            if fix_commands_in_file(file_path):
                total_fixed += 1
        else:
            print(f"❌ Archivo no encontrado: {file_path}")
    
    print(f"\n🎉 Proceso completado. {total_fixed} archivos actualizados.")

if __name__ == "__main__":
    main()
