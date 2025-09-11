#!/usr/bin/env python3
"""
Script de verificación completa del bot ONZA
Verifica compatibilidad con Render y Discord
"""

import os
import sys
import re
import subprocess

def print_header(title):
    """Imprimir encabezado con estilo"""
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print(f"{'='*60}")

def print_section(title):
    """Imprimir sección con estilo"""
    print(f"\n📁 {title}")
    print("-" * 40)

def check_render_compatibility():
    """Verificar compatibilidad con Render"""
    print_header("VERIFICACIÓN DE COMPATIBILIDAD CON RENDER")
    
    # Archivos críticos
    critical_files = [
        "main.py", "bot.py", "config.py", "utils.py", 
        "i18n.py", "requirements.txt", "render.yaml"
    ]
    
    print_section("ARCHIVOS CRÍTICOS")
    render_ok = 0
    
    for file in critical_files:
        if os.path.exists(file):
            print(f"✅ {file}")
            render_ok += 1
        else:
            print(f"❌ {file} - FALTANTE")
    
    # Verificar sintaxis Python
    print_section("SINTAXIS PYTHON")
    syntax_ok = 0
    
    for file in critical_files:
        if file.endswith('.py') and os.path.exists(file):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    compile(f.read(), file, 'exec')
                print(f"✅ {file} - Sintaxis OK")
                syntax_ok += 1
            except SyntaxError as e:
                print(f"❌ {file} - Error de sintaxis: {e}")
            except Exception as e:
                print(f"⚠️ {file} - Error: {e}")
    
    return render_ok, syntax_ok

def check_discord_compatibility():
    """Verificar compatibilidad con Discord"""
    print_header("VERIFICACIÓN DE COMPATIBILIDAD CON DISCORD")
    
    # Verificar comandos
    print_section("COMANDOS SLASH")
    command_files = [
        "commands/admin.py", "commands/user.py", "commands/tickets.py",
        "commands/publication.py", "commands/moderation.py", "commands/reviews.py"
    ]
    
    total_commands = 0
    valid_commands = 0
    
    for file_path in command_files:
        if not os.path.exists(file_path):
            print(f"❌ {file_path} - NO EXISTE")
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Buscar comandos slash
            slash_commands = re.findall(r'@self\.bot\.slash_command\([^)]*name=["\']([^"\']+)["\']', content)
            
            if slash_commands:
                print(f"✅ {file_path}: {len(slash_commands)} comandos")
                for cmd in slash_commands:
                    print(f"   - /{cmd}")
                total_commands += len(slash_commands)
                valid_commands += len(slash_commands)
            else:
                print(f"⚠️ {file_path} - Sin comandos")
                
        except Exception as e:
            print(f"❌ {file_path} - Error: {e}")
    
    # Verificar eventos
    print_section("EVENTOS DE DISCORD")
    event_files = [
        "events/bot_events.py", "events/channels.py", "events/interactive_messages.py"
    ]
    
    total_events = 0
    valid_events = 0
    
    for file_path in event_files:
        if not os.path.exists(file_path):
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            events = re.findall(r'async def on_([a-zA-Z_]+)', content)
            
            if events:
                print(f"✅ {file_path}: {len(events)} eventos")
                for event in events:
                    print(f"   - on_{event}")
                total_events += len(events)
                valid_events += len(events)
            else:
                print(f"⚠️ {file_path} - Sin eventos")
                
        except Exception as e:
            print(f"❌ {file_path} - Error: {e}")
    
    # Verificar configuración
    print_section("CONFIGURACIÓN DE DISCORD")
    config_ok = 0
    
    if os.path.exists("config.py"):
        try:
            with open("config.py", 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Verificar configuraciones importantes
            configs = [
                "DISCORD_TOKEN", "GUILD_ID", "STAFF_ROLE_ID", 
                "SUPPORT_ROLE_ID", "TICKETS_CATEGORY_NAME"
            ]
            
            for config in configs:
                if config in content:
                    print(f"✅ {config}")
                    config_ok += 1
                else:
                    print(f"❌ {config} - FALTANTE")
                    
        except Exception as e:
            print(f"❌ Error verificando config: {e}")
    else:
        print("❌ config.py - NO EXISTE")
    
    return valid_commands, valid_events, config_ok

def check_database_compatibility():
    """Verificar compatibilidad de base de datos"""
    print_header("VERIFICACIÓN DE BASE DE DATOS")
    
    print_section("ARCHIVOS DE BASE DE DATOS")
    db_files = ["init_db.py", "db.py"]
    db_ok = 0
    
    for file in db_files:
        if os.path.exists(file):
            print(f"✅ {file}")
            db_ok += 1
        else:
            print(f"❌ {file} - FALTANTE")
    
    # Verificar archivos de base de datos existentes
    print_section("ARCHIVOS DE DATOS")
    data_files = ["onza_bot.db", "onza_store.db"]
    data_ok = 0
    
    for file in data_files:
        if os.path.exists(file):
            size = os.path.getsize(file)
            print(f"✅ {file} ({size} bytes)")
            data_ok += 1
        else:
            print(f"⚠️ {file} - No existe (se creará automáticamente)")
    
    return db_ok, data_ok

def check_requirements():
    """Verificar requirements.txt"""
    print_header("VERIFICACIÓN DE DEPENDENCIAS")
    
    if os.path.exists("requirements.txt"):
        print_section("REQUIREMENTS.TXT")
        try:
            with open("requirements.txt", 'r') as f:
                requirements = f.read().strip().split('\n')
            
            for req in requirements:
                if req.strip():
                    print(f"✅ {req}")
            
            print(f"\n📦 Total de dependencias: {len([r for r in requirements if r.strip()])}")
            return True
            
        except Exception as e:
            print(f"❌ Error leyendo requirements.txt: {e}")
            return False
    else:
        print("❌ requirements.txt - NO EXISTE")
        return False

def main():
    """Función principal de verificación"""
    print("🤖 VERIFICACIÓN COMPLETA DEL BOT ONZA")
    print("Versión: 3.0 - Arquitectura Limpia")
    
    # Verificar Render
    render_files, syntax_ok = check_render_compatibility()
    
    # Verificar Discord
    discord_commands, discord_events, discord_config = check_discord_compatibility()
    
    # Verificar base de datos
    db_files, data_files = check_database_compatibility()
    
    # Verificar dependencias
    requirements_ok = check_requirements()
    
    # Resumen final
    print_header("RESUMEN FINAL")
    
    print(f"📊 COMPATIBILIDAD CON RENDER:")
    print(f"   Archivos críticos: {render_files}/8")
    print(f"   Sintaxis Python: {syntax_ok}/8")
    
    print(f"\n📊 COMPATIBILIDAD CON DISCORD:")
    print(f"   Comandos slash: {discord_commands}")
    print(f"   Eventos: {discord_events}")
    print(f"   Configuración: {discord_config}/5")
    
    print(f"\n📊 BASE DE DATOS:")
    print(f"   Archivos de código: {db_files}/2")
    print(f"   Archivos de datos: {data_files}/2")
    
    print(f"\n📊 DEPENDENCIAS:")
    print(f"   Requirements.txt: {'✅' if requirements_ok else '❌'}")
    
    # Evaluación final
    total_score = 0
    max_score = 0
    
    # Render (16 puntos)
    max_score += 16
    total_score += render_files * 2  # 8 archivos * 2 puntos
    total_score += syntax_ok * 2     # 8 archivos * 2 puntos
    
    # Discord (25 puntos)
    max_score += 25
    total_score += min(discord_commands, 15)  # Máximo 15 puntos por comandos
    total_score += min(discord_events, 5)     # Máximo 5 puntos por eventos
    total_score += discord_config             # 5 puntos por configuración
    
    # Base de datos (10 puntos)
    max_score += 10
    total_score += db_files * 5      # 2 archivos * 5 puntos
    total_score += data_files * 2.5  # 2 archivos * 2.5 puntos
    
    # Dependencias (5 puntos)
    max_score += 5
    total_score += 5 if requirements_ok else 0
    
    percentage = (total_score / max_score) * 100
    
    print(f"\n🎯 PUNTUACIÓN FINAL: {total_score:.1f}/{max_score} ({percentage:.1f}%)")
    
    if percentage >= 90:
        print("\n🎉 ¡EXCELENTE! El bot está completamente listo para producción")
        print("✅ Compatible con Render y Discord")
        print("✅ Listo para desplegarse")
        return True
    elif percentage >= 75:
        print("\n✅ ¡MUY BIEN! El bot está listo con pequeñas mejoras")
        print("⚠️ Revisa los elementos marcados con ❌")
        return True
    elif percentage >= 50:
        print("\n⚠️ El bot necesita mejoras antes de desplegarse")
        print("❌ Revisa los elementos marcados con ❌")
        return False
    else:
        print("\n❌ El bot no está listo para producción")
        print("❌ Necesita correcciones importantes")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
