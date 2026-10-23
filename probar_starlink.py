#!/usr/bin/env python3
"""Consulta de solo lectura para sparky8512/starlink-grpc-tools.

Guardar junto a starlink_grpc.py, instalar requirements.txt y ejecutar:
    python probar_starlink.py
    python probar_starlink.py --intervalo 5
Fuente: https://github.com/sparky8512/starlink-grpc-tools
"""

import argparse
from datetime import datetime
import math
import sys
import time


def numero(valor, factor=1, unidad=""):
    if valor is None:
        return "No disponible"
    return f"{valor * factor:.2f} {unidad}".strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destino", default="192.168.100.1:9200",
                        help="Direccion IP:puerto de la antena")
    parser.add_argument("--intervalo", type=float, default=0,
                        help="Segundos entre consultas; 0 = una consulta")
    args = parser.parse_args()
    if not math.isfinite(args.intervalo) or args.intervalo < 0:
        parser.error("El intervalo debe ser un numero finito mayor o igual a 0")

    try:
        import starlink_grpc
    except ImportError as exc:
        print(f"No se pudo importar el modulo: {exc}", file=sys.stderr)
        print("Guarda este script junto a starlink_grpc.py e instala las dependencias:"
              "\npython -m pip install -r requirements.txt", file=sys.stderr)
        return 1

    context = starlink_grpc.ChannelContext(target=args.destino)
    print(f"Consultando Starlink en {args.destino}. Ctrl+C para salir.")
    try:
        while True:
            try:
                grupos = starlink_grpc.status_data(context=context)
                estado = grupos[0]
                alertas = grupos[2]
            except starlink_grpc.GrpcError as exc:
                print(f"Error de consulta: {exc}", file=sys.stderr)
                print("Verifica acceso a 192.168.100.1, puerto TCP 9200, "
                      "rutas del router y VPN. Si TCP responde, revisa "
                      "compatibilidad del firmware y dependencias.", file=sys.stderr)
                return 1

            print("\n" + datetime.now().astimezone().isoformat(timespec="seconds"))
            print("Estado:", estado.get("state") or "No disponible")
            print("Hardware:", estado.get("hardware_version") or "No disponible")
            print("Firmware:", estado.get("software_version") or "No disponible")
            print("Tiempo encendida:", numero(estado.get("uptime"), 1 / 3600, "h"))
            print("Latencia al PoP:", numero(estado.get("pop_ping_latency_ms"), 1, "ms"))
            print("Perdida de ping:", numero(estado.get("pop_ping_drop_rate"), 100, "%"))
            print("Trafico de bajada:", numero(estado.get("downlink_throughput_bps"), 1e-6, "Mbps"))
            print("Trafico de subida:", numero(estado.get("uplink_throughput_bps"), 1e-6, "Mbps"))
            print("Fraccion obstruida:", numero(estado.get("fraction_obstructed"), 100, "%"))
            activas = [nombre for nombre, valor in alertas.items() if valor]
            print("Alertas activas:", ", ".join(activas) if activas else
                  ("Ninguna" if alertas else "No disponibles"))
            if args.intervalo == 0:
                return 0
            time.sleep(args.intervalo)
    except KeyboardInterrupt:
        print("\nConsulta finalizada.")
        return 0
    finally:
        context.close()


if __name__ == "__main__":
    sys.exit(main())
