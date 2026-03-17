import sys
import traceback
from datetime import datetime

from config import LOOP_INTERVAL, APP_NAME, APP_ENV
from live_engine import run_live_engine


def log_startup():
    print("\n" + "=" * 50)
    print(f"{APP_NAME} - INICIO")
    print("=" * 50)
    print(f"Hora inicio: {datetime.now().isoformat()}")
    print(f"Entorno: {APP_ENV}")
    print(f"Loop interval: {LOOP_INTERVAL} segundos")
    print("=" * 50 + "\n")


def log_shutdown():
    print("\n" + "=" * 50)
    print(f"{APP_NAME} - DETENIDO")
    print(f"Hora: {datetime.now().isoformat()}")
    print("=" * 50 + "\n")


def main():
    try:
        log_startup()

        run_live_engine(interval_seconds=LOOP_INTERVAL)

    except KeyboardInterrupt:
        print("\nInterrupción manual detectada (CTRL+C)")
        log_shutdown()
        sys.exit(0)

    except Exception as e:
        print("\n❌ ERROR CRÍTICO EN MAIN")
        print(f"Tipo: {type(e).__name__}")
        print(f"Mensaje: {str(e)}")
        print("\nTrace completo:")
        traceback.print_exc()

        log_shutdown()
        sys.exit(1)


if __name__ == "__main__":
    main()