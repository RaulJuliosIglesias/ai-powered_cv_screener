#!/usr/bin/env python3
"""
Smart API starter that finds an available port automatically.
"""
import socket
import sys
import subprocess
import os


def find_available_port(start_port=8000, max_attempts=10):
    """Find an available port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"No available ports found in range {start_port}-{start_port + max_attempts}")


if __name__ == "__main__":
    # Set UTF-8 encoding for Windows console
    if sys.platform == "win32":
        os.system("chcp 65001 >nul 2>&1")
    
    try:
        port = find_available_port()
        print(f"[API] Starting on port {port}...")
        
        # Start uvicorn
        subprocess.run([
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--host", "127.0.0.1",
            "--port", str(port),
            "--reload"
        ], cwd="backend")
    except KeyboardInterrupt:
        print("\n[API] Stopped")
    except Exception as e:
        print(f"[API] Error: {e}", file=sys.stderr)
        sys.exit(1)
