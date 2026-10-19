"""
Ampliacion institucional de SHARK V15 (seccion 15 de la especificacion).

Por defecto este paquete esta en modo OBSERVE: calcula, registra en su
propia tabla y no cambia ni una decision del nucleo. Nada de aqui puede
abrir, cerrar, ni mover el stop de una posicion de Shark.

Lo que hay y lo que no:

  M01 costes          implementado, en observacion. El umbral economico
                      esta UNSUPPORTED a proposito: no tenemos un
                      estimador de ganancia esperada validado fuera de
                      muestra, y el documento prohibe fabricarlo
                      convirtiendo un RSI o un momentum.
  M02 tendencia       implementado como contexto. Como estrategia
                      propia, sin presupuesto: medida, no autorizada.
  M03 ranking 12-1    igual que M02.
  M04 riesgo cartera  pendiente.
  M05 pares           BLOQUEADO. Exige cortos ejecutables y prestamo de
                      valores; la cuenta es al contado. La
                      configuracion lo rechaza por codigo.
  M06 fundamentales   BLOQUEADO. Exige fundamentales point-in-time;
                      yfinance da ratios actuales, que no sirven para
                      un backtest valido.
"""

from institucional.configuracion import (  # noqa: F401
    ENFORCE,
    OBSERVE,
    OFF,
    Extension,
    desde_entorno,
    validar,
)

__all__ = ["OFF", "OBSERVE", "ENFORCE", "Extension", "validar", "desde_entorno"]
