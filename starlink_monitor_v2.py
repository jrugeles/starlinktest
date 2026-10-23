#!/usr/bin/env python3
"""Monitor Starlink v2. Solo lectura. Python 3 + Tk + matplotlib.
Guardar junto a starlink_grpc.py. Instalar requirements.txt de este proyecto
en el mismo interprete de Thonny. Ejecutar con F5.
CSV y resumen JSON se guardan automaticamente en sesiones_starlink, junto
al script. --demo usa datos SINTETICOS y no consulta ninguna antena.
Fuente API: https://github.com/sparky8512/starlink-grpc-tools
"""
import csv
import json
import math
from pathlib import Path
import queue
import statistics
import sys
import threading
import time
from datetime import datetime, timezone
from collections import deque

KEYS = ['pop_ping_latency_ms', 'pop_ping_drop_rate',
        'downlink_throughput_bps', 'uplink_throughput_bps', 'power_w']
FIELDS = ['utc_estimada', 'segmento', 'contador'] + KEYS


def finite(v):
    return isinstance(v, (float, int)) and math.isfinite(v)


def percentile(values, p):
    if not values:
        return None
    s = sorted(values)
    k = (len(s) - 1) * p
    a = int(k)
    return s[a] + (s[min(a + 1, len(s) - 1)] - s[a]) * (k - a)


def fmt(v, suffix=''):
    return f'{v:.2f}{suffix}' if finite(v) else 'N/D'


class SessionData:
    """Deduplicacion por contador; cada reinicio/hueco rompe las rachas."""
    def __init__(self):
        self.last = None
        self.segment = 0
        self.anchor = None
        self.rows = deque(maxlen=1800)
        self.latencies = []
        self.n = self.loss_n = self.loss_sum = 0
        self.runs = self.run = self.max_run = self.full_loss = 0
        self.missing = self.resets = 0
        self.totals = {k: [0.0, 0] for k in KEYS[2:]}

    def ingest(self, general, bulk, received):
        end = general.get('end_counter')
        n = general.get('samples', 0)
        if end is None or n <= 0:
            return [], []
        notes = []
        first = end - n + 1
        reset = self.last is not None and end < self.last
        gap = self.last is not None and not reset and first > self.last + 1
        if reset or gap:
            self.segment += 1
            self.run = 0
            self.anchor = None
            if reset:
                self.resets += 1
                notes.append('Contador reiniciado: nuevo segmento; posible reinicio de antena.')
            else:
                lost = first - self.last - 1
                self.missing += lost
                notes.append(f'Hueco de {lost} muestras no recuperadas; no se cuenta como perdida de ping.')
        if self.anchor is None:
            self.anchor = received - end
        result = []
        for i in range(n):
            counter = first + i
            if not reset and self.last is not None and counter <= self.last:
                continue
            row = {'utc_estimada': datetime.fromtimestamp(self.anchor + counter, timezone.utc).isoformat(),
                   'segmento': self.segment, 'contador': counter}
            for key in KEYS:
                seq = bulk.get(key, [])
                v = seq[i] if i < len(seq) else None
                row[key] = v if finite(v) else None
            loss = row[KEYS[1]]
            if loss is not None and not 0 <= loss <= 1:
                row[KEYS[1]] = loss = None
            if loss == 1:
                row[KEYS[0]] = None
            lat = row[KEYS[0]]
            if lat is not None and lat >= 0:
                self.latencies.append(lat)
            if loss is not None:
                self.loss_sum += loss
                self.loss_n += 1
            if loss == 1:
                if self.run == 0:
                    self.runs += 1
                self.run += 1
                self.full_loss += 1
                self.max_run = max(self.max_run, self.run)
            else:
                self.run = 0
            for key, total in self.totals.items():
                v = row[key]
                if v is not None and v >= 0:
                    total[0] += v
                    total[1] += 1
            self.n += 1
            self.rows.append(row)
            result.append(row)
        self.last = end
        return result, notes

    def summary(self):
        def integral(k, factor):
            total, count = self.totals[k]
            return total * factor if count else None
        power, power_n = self.totals['power_w']
        return {'muestras': self.n,
                'latencia_media_ms': statistics.mean(self.latencies) if self.latencies else None,
                'latencia_p95_ms': percentile(self.latencies, .95),
                'perdida_media_pct': 100 * self.loss_sum / self.loss_n if self.loss_n else None,
                'muestras_con_perdida_valida': self.loss_n,
                'rachas_perdida_completa_observadas': self.runs,
                'segundos_perdida_completa_observados': self.full_loss,
                'racha_max_observada_s': self.max_run,
                'muestras_no_recuperadas': self.missing, 'reinicios_contador': self.resets,
                'descarga_MB_observados': integral(KEYS[2], 1 / 8e6),
                'subida_MB_observados': integral(KEYS[3], 1 / 8e6),
                'potencia_media_W': power / power_n if power_n else None,
                'energia_Wh_observada': integral('power_w', 1 / 3600),
                'muestras_validas_trafico_potencia': {k: v[1] for k, v in self.totals.items()}}


def main():
    import tkinter as tk
    from tkinter import ttk, messagebox
    try:
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        import numpy as np
    except ImportError as e:
        messagebox.showerror('Dependencias', f'{e}\nInstala matplotlib en el Python de Thonny:\npython -m pip install matplotlib')
        return
    demo = '--demo' in sys.argv
    root = tk.Tk()
    root.title('Wirid-LAB | Starlink Monitor v2' + (' | DEMOSTRACION SINTETICA' if demo else ''))
    root.geometry('1180x850')
    root.minsize(920, 700)
    root.columnconfigure(0, weight=1)
    root.rowconfigure(3, weight=1)
    events = queue.Queue()
    stop = threading.Event()
    map_request = threading.Event()
    state = {'active': False, 'session': None, 'file': None, 'writer': None,
             'path': None, 'errors': 0, 'worker': None}
    target = tk.StringVar(value='192.168.100.1:9200')
    interval = tk.StringVar(value='5')
    past = tk.BooleanVar(value=False)
    status = tk.StringVar(value='Listo. Inicia una sesion para consultar la antena.')
    metrics = tk.StringVar(value='Sin muestras')
    folder = tk.StringVar(value='Los resultados se guardan junto al programa, en sesiones_starlink.')
    bar = ttk.Frame(root, padding=10)
    bar.grid(row=0, column=0, sticky='ew')
    ttk.Label(bar, text='Antena IP:puerto').pack(side='left')
    entry = ttk.Entry(bar, textvariable=target, width=24)
    entry.pack(side='left', padx=6)
    ttk.Label(bar, text='Consulta cada (s)').pack(side='left')
    spin = ttk.Spinbox(bar, from_=1, to=300, textvariable=interval, width=5)
    spin.pack(side='left', padx=6)
    check = ttk.Checkbutton(bar, text='Incluir historial previo', variable=past)
    check.pack(side='left', padx=6)
    ttk.Label(root, textvariable=status, padding=(10, 3), wraplength=1100).grid(row=1, column=0, sticky='w')
    ttk.Label(root, textvariable=metrics, padding=10, font=('Segoe UI', 10)).grid(row=2, column=0, sticky='w')
    tabs = ttk.Notebook(root)
    tabs.grid(row=3, column=0, sticky='nsew', padx=10)
    graph_tab, map_tab, log_tab = (ttk.Frame(tabs) for _ in range(3))
    for frame, name in [(graph_tab, 'Enlace'), (map_tab, 'Obstrucciones'), (log_tab, 'Eventos')]:
        tabs.add(frame, text=name)
    fig = Figure(figsize=(10, 5.5), dpi=100, constrained_layout=True)
    axes = fig.subplots(3, 1, sharex=True)
    canvas = FigureCanvasTkAgg(fig, graph_tab)
    canvas.get_tk_widget().pack(fill='both', expand=True)
    ttk.Label(map_tab, text='Solicita el mapa durante una sesion. Indices de matriz; no son azimut/elevacion.').pack(pady=8)
    mfig = Figure(figsize=(8, 5), dpi=100, constrained_layout=True)
    maxis = mfig.add_subplot(111)
    maxis.set_title('Sin mapa: pulsa Consultar mapa')
    mcanvas = FigureCanvasTkAgg(mfig, map_tab)
    mcanvas.get_tk_widget().pack(fill='both', expand=True)
    log = tk.Text(log_tab, height=10, state='disabled', wrap='word')
    log.pack(fill='both', expand=True)
    ttk.Label(root, textvariable=folder, wraplength=1100, padding=(10, 5)).grid(row=4, column=0, sticky='w')
    ttk.Label(root, text='Trafico observado, no speed test. Latencia al PoP. UTC estimada desde el reloj del PC; muestras de 1 s.\n'
              'Resumen: solo datos capturados (incluye historial previo si se selecciona). Graficas: ultimas 1800 muestras.',
              padding=(10, 5)).grid(row=5, column=0, sticky='w')

    def note(msg):
        text = datetime.now().astimezone().isoformat(timespec='seconds') + '  ' + msg
        log.configure(state='normal')
        log.insert('end', text + '\n')
        log.see('end')
        log.configure(state='disabled')
        if state['path']:
            with (state['path'] / 'eventos.txt').open('a', encoding='utf-8') as f:
                f.write(text + '\n')

    def summary_save():
        if not state['session']:
            return
        data = state['session'].summary()
        data.update({'demo_sintetica': demo, 'errores_consulta_local': state['errors'],
                     'nota': 'UTC estimada, no hora GPS. Integracion con muestras de 1 segundo. '
                     'Rachas en bordes/huecos pueden estar incompletas. Huecos excluidos de metricas. '
                     'Latencia solo para muestras con respuesta. Trafico no representa capacidad maxima.'})
        (state['path'] / 'resumen.json').write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')

    def draw():
        s = state['session']
        if s is None:
            return
        data = s.summary()
        metrics.set(f"Muestras: {s.n}  |  Latencia media: {fmt(data['latencia_media_ms'], ' ms')}  |  P95: {fmt(data['latencia_p95_ms'], ' ms')}\n"
                    f"Perdida media: {fmt(data['perdida_media_pct'], ' %')}  |  Rachas de perdida completa: {s.runs}  |  Max: {s.max_run} s  |  Huecos: {s.missing}\n"
                    f"Bajada: {fmt(data['descarga_MB_observados'], ' MB')}  |  Subida: {fmt(data['subida_MB_observados'], ' MB')}  |  Potencia: {fmt(data['potencia_media_W'], ' W')}")
        rows = list(s.rows)
        for ax in axes:
            ax.clear()
            ax.grid(alpha=.25)
        if rows:
            from matplotlib.dates import DateFormatter
            # Separar segmentos con NaN para no unir huecos/reinicios.
            x, ys = [], [[] for _ in KEYS]
            previous = None
            for row in rows:
                dt = datetime.fromisoformat(row['utc_estimada'])
                if previous is not None and row['segmento'] != previous:
                    x.append(dt)
                    for y in ys:
                        y.append(float('nan'))
                x.append(dt)
                for y, key in zip(ys, KEYS):
                    y.append(row[key] if row[key] is not None else float('nan'))
                previous = row['segmento']
            axes[0].plot(x, ys[0], color='#1976d2', linewidth=1)
            axes[1].plot(x, np.array(ys[1]) * 100, color='#d84315', linewidth=1)
            axes[2].plot(x, np.array(ys[2]) / 1e6, label='Bajada', linewidth=1)
            axes[2].plot(x, np.array(ys[3]) / 1e6, label='Subida', linewidth=1)
            axes[2].legend(loc='upper left')
            axes[2].xaxis.set_major_formatter(DateFormatter('%H:%M:%S', tz=timezone.utc))
        axes[0].set_ylabel('Latencia (ms)')
        axes[1].set_ylabel('Perdida (%)')
        axes[1].set_ylim(-2, 102)
        axes[2].set_ylabel('Trafico (Mbps)')
        axes[2].set_xlabel('UTC estimada')
        canvas.draw_idle()

    def worker(address, seconds, include_past):
        context = None
        cursor = None
        initialized = False
        try:
            if not demo:
                import starlink_grpc as api
                context = api.ChannelContext(target=address)
            demo_counter = 1000
            while not stop.is_set():
                try:
                    if demo:
                        n = 60 if not initialized and include_past else (1 if not initialized else max(1, int(seconds)))
                        demo_counter += n
                        counters = list(range(demo_counter-n+1, demo_counter+1))
                        bulk = {KEYS[0]: [30+10*math.sin(c/15) for c in counters],
                                KEYS[1]: [1.0 if c % 60 in (0, 1) else 0.0 for c in counters],
                                KEYS[2]: [(12+8*math.sin(c/10))*1e6 for c in counters],
                                KEYS[3]: [2e6 for c in counters], 'power_w': [25.0 for c in counters]}
                        general = {'end_counter': demo_counter, 'samples': n}
                        st = {'state': 'DEMO SINTETICA', 'hardware_version': 'SIMULADO'}
                    else:
                        try:
                            groups = api.status_data(context=context)
                            st = groups[0]
                            active = [k for k, v in groups[2].items() if v]
                            events.put(('status', f"{st.get('state', 'N/D')} | {st.get('hardware_version', 'N/D')} | Alertas: {', '.join(active) or 'ninguna reportada'}"))
                        except Exception as e:
                            events.put(('error', 'Estado: ' + str(e)))
                        history = api.get_history(context=context)
                        current = int(history.current)
                        if not initialized and not include_past:
                            # Establecer frontera: la sesion empieza en esta lectura.
                            cursor = current
                        general, bulk = api.history_bulk_data(-1, start=cursor, history=history)
                    if general.get('end_counter') is None:
                        raise ValueError('Historial sin contador compatible; actualiza el repositorio.')
                    cursor = general['end_counter']
                    initialized = True
                    events.put(('batch', (general, bulk, time.time())))
                    if demo:
                        events.put(('status', 'DEMO SINTETICA: no son mediciones de tu antena'))
                except Exception as e:
                    events.put(('error', 'Historial: ' + str(e)))
                if map_request.is_set():
                    map_request.clear()
                    try:
                        if demo:
                            yy, xx = np.mgrid[-1:1:80j, -1:1:80j]
                            array = np.where(xx*xx+yy*yy<1, np.clip(1-xx*xx, 0, 1), -1)
                        else:
                            array = np.array(api.obstruction_map(context=context), dtype=float)
                        events.put(('map', array))
                    except Exception as e:
                        events.put(('error', 'Mapa: ' + str(e)))
                stop.wait(seconds)
        except Exception as e:
            events.put(('error', f'No se pudo iniciar: {e}. Revisa dependencias en el interprete de Thonny.'))
        finally:
            if context is not None:
                context.close()
            events.put(('done', None))

    def start():
        try:
            seconds = float(interval.get())
            if not math.isfinite(seconds) or not 1 <= seconds <= 300:
                raise ValueError()
        except ValueError:
            messagebox.showerror('Intervalo', 'Elige entre 1 y 300 segundos.')
            return
        try:
            path = Path(__file__).resolve().parent / 'sesiones_starlink' / (('DEMO_' if demo else '') + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
            path.mkdir(parents=True)
            file = (path / 'historial.csv').open('w', newline='', encoding='utf-8')
        except OSError as e:
            messagebox.showerror('Guardado', str(e))
            return
        state.update(active=True, session=SessionData(), file=file, writer=csv.DictWriter(file, fieldnames=FIELDS), path=path, errors=0)
        state['writer'].writeheader()
        file.flush()
        stop.clear()
        map_request.clear()
        begin.configure(state='disabled')
        end.configure(state='normal')
        map_button.configure(state='normal')
        for w in (entry, spin, check):
            w.configure(state='disabled')
        folder.set(str(path))
        status.set('Conectando... La primera consulta puede tardar.')
        note('Inicio de sesion' + (' SINTETICA' if demo else '') + f'; historial previo: {past.get()}')
        state['worker'] = threading.Thread(target=worker, args=(target.get().strip(), seconds, past.get()), daemon=True)
        state['worker'].start()

    def halt():
        stop.set()
        end.configure(state='disabled')
        map_button.configure(state='disabled')
        status.set('Deteniendo: esperando que termine la consulta pendiente...')

    def finish():
        summary_save()
        if state['file']:
            state['file'].close()
            state['file'] = None
        state['active'] = False
        begin.configure(state='normal')
        end.configure(state='disabled')
        map_button.configure(state='disabled')
        for w in (entry, spin, check):
            w.configure(state='normal')
        status.set('Sesion terminada. CSV y resumen guardados.')

    def process():
        dirty = False
        try:
            while True:
                kind, payload = events.get_nowait()
                if kind == 'batch':
                    rows, notes = state['session'].ingest(*payload)
                    state['writer'].writerows(rows)
                    state['file'].flush()
                    for msg in notes:
                        note(msg)
                    dirty = True
                elif kind == 'status':
                    if not stop.is_set():
                        status.set(payload)
                elif kind == 'error':
                    state['errors'] += 1
                    status.set('Error de consulta local; se reintentara. Ver Eventos.')
                    note(payload)
                elif kind == 'map':
                    array = payload
                    if array.ndim != 2 or not array.size:
                        note('Mapa vacio/no compatible.')
                        continue
                    mfig.clear()
                    ax = mfig.add_subplot(111)
                    cmap = __import__('matplotlib').colormaps['RdYlGn'].copy()
                    cmap.set_bad('#cbd5e1')
                    im = ax.imshow(np.ma.masked_where((array < 0) | ~np.isfinite(array), array), vmin=0, vmax=1, cmap=cmap, origin='upper')
                    ax.set_title('Mapa reportado' + (' — DEMO SINTETICA' if demo else ''))
                    ax.set_xlabel('Columna (gris: sin datos)')
                    ax.set_ylabel('Fila')
                    mfig.colorbar(im, ax=ax, label='Valor normalizado del mapa (no dB)')
                    stamp = datetime.now().strftime('%H%M%S_%f')
                    mfig.savefig(state['path'] / f'mapa_{stamp}.png', dpi=150)
                    np.savetxt(state['path'] / f'mapa_{stamp}.csv', array, delimiter=',')
                    mcanvas.draw_idle()
                    note('Mapa guardado como PNG y CSV.')
                elif kind == 'done':
                    note('Fin de adquisicion.')
                    finish()
        except queue.Empty:
            pass
        except OSError as e:
            stop.set()
            status.set('ERROR DE GUARDADO: ' + str(e))
            messagebox.showerror('Error de guardado', str(e))
        if dirty:
            draw()
            try:
                summary_save()
            except OSError as e:
                stop.set()
                status.set('ERROR DE GUARDADO: ' + str(e))
        root.after(300, process)

    def close():
        if state['active']:
            halt()
            # Esperar asincronamente; mantener la interfaz y drenar resultados.
            root.after(300, close)
            return
        root.destroy()

    begin = ttk.Button(bar, text='Iniciar', command=start)
    begin.pack(side='left', padx=4)
    end = ttk.Button(bar, text='Detener', command=halt, state='disabled')
    end.pack(side='left', padx=4)
    map_button = ttk.Button(bar, text='Consultar mapa', command=map_request.set, state='disabled')
    map_button.pack(side='left', padx=4)
    root.protocol('WM_DELETE_WINDOW', close)
    root.after(300, process)
    root.mainloop()


if __name__ == '__main__':
    main()
