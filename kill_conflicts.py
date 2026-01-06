#!/usr/bin/env python3
"""
Script para limpiar procesos conflictivos en puertos 8000, 8001 y 6001
"""
import subprocess
import sys
import time

def kill_processes_on_ports():
    """Mata procesos en puertos conflictivos"""
    ports_to_check = [8000, 8001, 6001]
    
    for port in ports_to_check:
        try:
            # Obtener PID del proceso usando el puerto
            result = subprocess.run(
                f'netstat -ano | findstr ":{port}.*LISTENING"',
                shell=True,
                capture_output=True,
                text=True
            )
            
            if result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 5:
                            pid = parts[-1]
                            try:
                                subprocess.run(f'taskkill /PID {pid} /F', shell=True)
                                print(f"✓ Proceso {pid} en puerto {port} terminado")
                            except:
                                pass
            else:
                print(f"✓ Puerto {port} libre")
                
        except Exception as e:
            print(f"Error checking port {port}: {e}")

if __name__ == "__main__":
    print("🧹 Limpiando puertos conflictivos...")
    kill_processes_on_ports()
    time.sleep(2)
    print("✨ ¡Listo! Puertos limpios.")
