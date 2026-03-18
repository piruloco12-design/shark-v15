import sys
import traceback
from datetime import datetime

from config import LOOP_INTERVAL, APP_NAME, APP_ENV
from live_engine import run_live_engine
from telegram_alerts import send_telegram_message


def log_startup():
    print("\n" + "=" * 50, flush=True)
    print(f"{APP_NAME} - INICIO", flush=True)
    print("=" * 50, flush=True)
    print(f"Hora inicio: {datetime.now().isoformat()}", flush=True)
    print(f"Entorno: {APP_ENV}", flush=True)
    print(f"Loop interval: {LOOP_INTERVAL} segundos", flush=True)
    print("=" * 50 + "\n", flush=True)


def log_shutdown():
    print("\n" + "=" * 50, flush=True)
    print(f"{APP_NAME} - DETENIDO", flush=True)
    print(f"Hora: {datetime.now().isoformat()}", flush=True)
    print("=" * 50 + "\n", flush=True)


def main():
    try:
        log_startup()
        run_live_engine(interval_seconds=LOOP_INTERVAL)

    except KeyboardInterrupt:
        print("\nInterrupción manual detectada (CTRL+C)", flush=True)
        log_shutdown()
        sys.exit(0)

    except Exception as e:
        print("\n❌ ERROR CRÍTICO EN MAIN", flush=True)
        print(f"Tipo: {type(e).__name__}", flush=True)
        print(f"Mensaje: {str(e)}", flush=True)
        print("\nTrace completo:", flush=True)
        traceback.print_exc()

        try:
            send_telegram_message(
                f"❌ SHARK ERROR EN MAIN: {type(e).__name__} - {str(e)}"
            )
        except Exception:
            print("No se pudo enviar alerta de error a Telegram.", flush=True)

        log_shutdown()
        sys.exit(1)


if __name__ == "__main__":
    main()