# Starlink Connectivity Lab

Herramientas educativas en Python para consultar y registrar la conectividad de una antena Starlink desde su red local.

**José Rugeles, Ph.D. · Wirid-LAB · Universidad Militar Nueva Granada**

El proyecto contiene dos programas utilizados en pruebas docentes con una **Starlink Mini**. Permite estudiar latencia al PoP, pérdida de ping, tráfico, consumo eléctrico reportado y mapas de obstrucciones. No es un producto oficial de SpaceX o Starlink.

## Programas

| Programa | Función | Interfaz | Salidas |
|---|---|---|---|
| [`probar_starlink.py`](probar_starlink.py) | Primera verificación de conectividad, estado, hardware, firmware y métricas actuales | Consola / Thonny | Texto; consulta única o periódica |
| [`starlink_monitor_v2.py`](starlink_monitor_v2.py) | Captura del historial, gráficas, resumen estadístico y consulta del mapa | Ventana Tkinter | CSV, JSON, eventos y mapas PNG/CSV |

El monitor recupera muestras históricas de aproximadamente un segundo, aunque la consulta se haga cada cinco segundos. Usa el contador de la antena para evitar duplicados y distingue huecos del historial de pérdidas de ping.

## Repositorio fuente y funciones utilizadas

La comunicación gRPC usa **[sparky8512/starlink-grpc-tools](https://github.com/sparky8512/starlink-grpc-tools)**. Se incluye su módulo `starlink_grpc.py` sin modificaciones, con procedencia y revisión en [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md). No hace falta clonar ese repositorio por separado.

| Función o clase de `starlink_grpc` | Uso | Programa | Resultado / observación |
|---|---|---|---|
| `ChannelContext(target=...)` | Crear y reutilizar el canal a `192.168.100.1:9200` | Ambos | Conexión local a la antena |
| `status_data(context=...)` | Consultar estado y alertas | Ambos | Tupla de diccionarios: estado, obstrucciones, alertas y actualización de software |
| `get_history(context=...)` | Recuperar el búfer histórico original | Monitor | Mensaje con contador y series; evita repetir la petición al analizarlo |
| `history_bulk_data(-1, start=..., history=...)` | Extraer solo muestras nuevas | Monitor | Contador final, cantidad de muestras y listas de latencia, pérdida, tráfico y potencia |
| `obstruction_map(context=...)` | Obtener una matriz del mapa | Monitor | Valores normalizados 0–1; valores negativos significan datos no válidos |
| `ChannelContext.close()` | Cerrar el canal al terminar | Ambos | Libera los recursos de conexión |
| `GrpcError` | Manejar errores de la biblioteca | Consulta básica | Diagnóstico de fallo de comunicación/protocolo; el monitor también captura otras excepciones |

Referencia de implementación: [`starlink_grpc.py` en el repositorio original](https://github.com/sparky8512/starlink-grpc-tools/blob/main/starlink_grpc.py).

El percentil 95, la integración de tráfico/energía, la detección de rachas, las gráficas y la exportación son cálculos de **nuestro monitor**; no se llama a `history_stats()`. Los programas no envían órdenes de reinicio, plegado ni borrado del mapa.

## Requisitos

- Un computador conectado a la red de la antena por Wi-Fi o Ethernet.
- Acceso local a **192.168.100.1, puerto TCP 9200**. Tener Internet mediante Starlink no garantiza que exista una ruta hacia esa dirección.
- Para un entorno homogéneo de clase, usar **Python 3.11 o 3.12** con Tkinter.
- Internet para instalar las dependencias. Las consultas a la antena se hacen por la red local, sin credenciales de una cuenta Starlink.
- Carpeta con permiso de escritura para los resultados.

### Librerías

| Paquete | Propósito |
|---|---|
| `grpcio` | Cliente gRPC |
| `grpcio-reflection` | Soporte del servicio de reflexión gRPC |
| `protobuf` | Mensajes Protocol Buffers |
| `yagrc` | Construcción dinámica del cliente a partir del esquema de la antena |
| `typing-extensions` | Compatibilidad de tipos usados por el módulo fuente |
| `matplotlib` | Gráficas y exportación PNG |
| `numpy` | Operaciones numéricas y matrices del mapa |
| `tkinter` | Ventana gráfica; se instala con Python o con el gestor del sistema, **no mediante pip** |

`csv`, `json`, `threading`, `queue`, `datetime`, `pathlib`, `statistics` y `argparse` pertenecen a la biblioteca estándar. No se requiere generar archivos `.proto` ni instalar `grpcio-tools` para estos dos programas: se usa reflexión.

`requirements.txt` declara rangos de dependencias; no es un entorno congelado probado en todas sus combinaciones. Tras validar el entorno de clase, puede registrarse con `python -m pip freeze > requirements-clase.txt`.

## Instalación en Windows desde terminal

Descarga este proyecto con **Code → Download ZIP**, extrae la carpeta completa y abre PowerShell dentro de ella. Conserva juntos los tres archivos Python.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Si usas Python 3.12, sustituye `py -3.11` por `py -3.12`. Los comandos siguientes usan el ejecutable del entorno directamente, sin activar scripts de PowerShell.

Comprueba los paquetes:

```powershell
.\.venv\Scripts\python.exe -c "import grpc, yagrc, numpy, matplotlib, tkinter, starlink_grpc; print('Dependencias OK')"
Test-NetConnection 192.168.100.1 -Port 9200
```

`TcpTestSucceeded : True` confirma acceso al puerto, no que todas las funciones del firmware sean compatibles.

## Instalación y uso en Thonny

1. Selecciona un intérprete **Python local**, no MicroPython/CircuitPython.
2. Para usar el entorno anterior, selecciona su ejecutable `.venv\Scripts\python.exe` en la configuración del intérprete de Thonny.
3. Alternativamente, instala los paquetes de la tabla mediante **Herramientas → Administrar paquetes**, en el intérprete que usarás para ejecutar.
4. Reinicia el intérprete después de instalar las librerías.
5. Abre `probar_starlink.py` y pulsa **F5**. Luego prueba `starlink_monitor_v2.py`.

Para saber qué Python usa realmente Thonny, ejecuta en su consola:

```python
import sys
print(sys.executable)
```

Si instalas desde otra terminal, usa esa ruta exacta con `-m pip install -r requirements.txt`. En PowerShell, una ruta entre comillas se ejecuta con `&` delante:

```powershell
& "C:\ruta\al\python.exe" -m pip install -r requirements.txt
```

## Instalación en Linux

Con Python y Tkinter instalados:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python probar_starlink.py
.venv/bin/python starlink_monitor_v2.py
```

En Debian/Ubuntu, si faltan los módulos del sistema, se pueden instalar con `sudo apt install python3-venv python3-tk`. La ventana requiere una sesión gráfica.

## Ejecución

### Programa 1: consulta básica

```powershell
.\.venv\Scripts\python.exe probar_starlink.py
.\.venv\Scripts\python.exe probar_starlink.py --intervalo 5
```

La primera orden consulta una vez. La segunda repite hasta pulsar **Ctrl+C**. Para una dirección distinta:

```powershell
.\.venv\Scripts\python.exe probar_starlink.py --destino 192.168.100.1:9200
```

### Programa 2: monitor

```powershell
.\.venv\Scripts\python.exe starlink_monitor_v2.py
```

1. Mantén el destino por defecto y un intervalo de **5 s**.
2. Decide si quieres **Incluir historial previo**. Desactivado, la primera lectura establece el punto de inicio y las siguientes añaden datos nuevos; activado, el resumen también incluye muestras anteriores al inicio.
3. Pulsa **Iniciar**. Cada inicio crea una carpeta nueva.
4. **Consultar mapa** solicita una captura en el siguiente ciclo. Selecciona la pestaña **Obstrucciones** para verla; se guarda automáticamente como PNG y CSV. No borra el mapa ni lo actualiza continuamente.
5. Pulsa **Detener** y espera a que termine la consulta pendiente. El CSV se crea al iniciar y se actualiza durante la captura, no solamente al detener.

Las gráficas muestran hasta las últimas 1800 muestras; el CSV y el resumen contienen toda la sesión capturada. El historial de la antena es limitado: una interrupción de acceso suficientemente larga puede impedir recuperar todas las muestras.

### Demostración sin antena

```powershell
.\.venv\Scripts\python.exe starlink_monitor_v2.py --demo
```

La interfaz y la carpeta identifican estos datos como **DEMO SINTÉTICA**. No deben mezclarse con mediciones reales.

## Archivos de salida y significado

Dentro de `sesiones_starlink/FECHA_HORA/`:

| Archivo | Contenido |
|---|---|
| `historial.csv` | Una fila por muestra recuperada |
| `resumen.json` | Latencia media/P95, pérdidas, rachas observadas, tráfico integrado y energía |
| `eventos.txt` | Inicio, fin, errores y huecos/reinicios detectados |
| `mapa_*.png` / `mapa_*.csv` | Capturas solicitadas del mapa |

El CSV usa coma como separador y punto decimal. En Excel, importa mediante **Datos → Desde texto/CSV** y selecciona el separador correcto. En MATLAB: `T = readtable("historial.csv");`.

| Columna | Unidad / interpretación |
|---|---|
| `utc_estimada` | Fecha ISO 8601 en UTC, estimada con reloj del PC y contador; no es una marca GPS de la antena |
| `segmento` | Separación al detectar retroceso del contador o hueco no recuperado |
| `contador` | Identificador secuencial de la muestra en la antena |
| `pop_ping_latency_ms` | Latencia al PoP en ms; vacía si no hay dato válido/respuesta |
| `pop_ping_drop_rate` | Fracción de pérdida 0–1; para porcentaje, multiplicar por 100 |
| `downlink_throughput_bps` / `uplink_throughput_bps` | Tráfico observado en bit/s; dividir por 1 000 000 para Mbps |
| `power_w` | Consumo eléctrico reportado en W; no es RSSI ni potencia de transmisión RF |

La media de pérdida es el promedio de las fracciones válidas por muestra; no se conocen aquí los conteos de paquetes para calcular otra ponderación. El P95 es el percentil por interpolación lineal de las latencias disponibles. Las rachas cuentan muestras consecutivas con pérdida 1; los huecos rompen la racha y sus bordes pueden quedar incompletos.

Se integra el tráfico suponiendo muestras de 1 s: **MB = Σ(bit/s) / 8 000 000**. Para energía: **Wh = Σ(W) / 3600**. Los datos ausentes no se sustituyen por cero; los totales solo cubren muestras disponibles. En Colombia, UTC−5 permite interpretar las horas locales de la práctica.

## Alcance de las mediciones

- El tráfico observado no es una prueba de capacidad máxima. Las descargas/subidas de prueba se generan por separado.
- La latencia es al PoP reportado por Starlink, no necesariamente a un servidor de Internet elegido por el estudiante.
- No se obtiene RSSI en dBm, I/Q ni identificación confirmada del satélite conectado.
- El SNR numérico está obsoleto en el módulo fuente. El mapa normalizado no tiene una conversión documentada a dB; sus ejes son índices de matriz, no azimut/elevación.
- Los cambios de latencia no prueban por sí solos un cambio de satélite.
- Los campos disponibles dependen del hardware y firmware; un valor no disponible no significa cero.
- Los retrocesos del contador permiten detectar posibles reinicios; no se garantiza detectar un reinicio si el nuevo contador ya superó el anterior durante una desconexión larga.

## Práctica sugerida

Registrar tres fases de cinco minutos: poco tráfico, descarga y subida. Mantener ubicación, orientación y conexión local; anotar hora de cada fase, aplicación usada, firmware y presencia de otros usuarios. No activar historial previo para comparar únicamente las fases de la práctica.

Comparar media, mediana y P95 de latencia, pérdida reportada, tráfico y potencia. Usar Ethernet cuando se busque reducir la variabilidad de la conexión local. El monitor no genera el tráfico de carga ni registra automáticamente las etiquetas de las fases.

## Solución de problemas

| Síntoma | Acción |
|---|---|
| `No module named 'grpc'` | Instalar `grpcio` o todos los requisitos en el Python indicado por `sys.executable` |
| `No module named 'starlink_grpc'` | Extraer la carpeta completa; el módulo incluido debe estar junto a los programas |
| Falta `matplotlib` o `numpy` | Ejecutar la instalación de `requirements.txt` en el mismo intérprete |
| No aparece la ventana | Abrir el archivo completo `starlink_monitor_v2.py`, verificar su llamada final a `main()` y revisar la consola |
| No conecta | Comprobar TCP 9200, ruta a 192.168.100.1, VPN y configuración del router propio/bypass |
| Mapa vacío o consulta rechazada | Consultar Eventos; comprobar disponibilidad en firmware y dar tiempo a acumular información |
| Ventana con pocos datos al inicio | Sin historial previo, esperar las siguientes consultas |
| Error de guardado | Mover el proyecto a una carpeta con permiso de escritura y espacio disponible |

## Validación y publicación

Los programas base se ejecutaron con una Starlink Mini durante una prueba del autor. El empaquetado incluye comprobaciones de sintaxis y pruebas sintéticas del procesamiento; no implica validación de todos los firmwares ni de todas las combinaciones de dependencias.

```bash
python -m compileall -q probar_starlink.py starlink_monitor_v2.py starlink_grpc.py
python -m unittest discover -s tests -v
```

Instrucciones para crear el repositorio remoto: [`docs/PUBLICAR_EN_GITHUB.md`](docs/PUBLICAR_EN_GITHUB.md).

Las capturas reales, entornos virtuales y resultados de sesiones están excluidos por `.gitignore`. La licencia del componente externo se conserva en `licenses/`; no se ha asignado una licencia de distribución a los dos programas docentes y su documentación. El titular puede elegirla antes de compartirlos para reutilización pública.
