#!/usr/bin/env python3
import subprocess
import sys
import os

def start_celery():
    """Démarrer le worker Celery"""
    cmd = [
        sys.executable, "-m", "celery",
        "-A", "app.core.celery_app",
        "worker",
        "--loglevel=info",
        "--concurrency=2"  # 2 workers simultanés
    ]
    
    print("🚀 Démarrage du worker Celery...")
    print(f"Commande: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n⏹️  Arrêt du worker Celery")
    except Exception as e:
        print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    start_celery()