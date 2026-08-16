#!/usr/bin/env python3
"""Genera estadísticas de los informes reales de la Manada LEONES.

Este script tiene una característica importante: una Manada recién instalada
puede tener **cero informes reales**. Eso es un estado válido, no un fallo.

Por tanto:
- los ejemplos ficticios nunca entran en las estadísticas;
- cero informes produce un README de estadísticas válido;
- las gráficas solo se crean cuando existen datos reales;
- no se inventan valores para conseguir una gráfica o una media.

La guía humana está en docs/MANADA_STATS.md y la documentación general de
componentes terminados en docs/completed/.
"""
from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path

# Matplotlib solo es necesario cuando existen datos. Importarlo dentro de main
# hace que la ruta «cero informes» sea independiente de la librería gráfica.
def load_matplotlib():
    try:
        import matplotlib.pyplot as plt
        return plt
    except ImportError as exc:
        raise SystemExit(
            'Falta matplotlib. Instala con: python3 -m pip install matplotlib'
        ) from exc


def rx(name):
    """Crea una expresión regular para una línea «- Nombre: valor»."""
    return re.compile(rf'^- {name}:\s*(.+)$', re.M)


RAM = rx('RAM')
CPU = rx('CPU')
OS = rx('Sistema')
GPU = rx('GPU')
PROFILE = rx('Perfil LEONES')
TOK = rx('Inferencia')
B = re.compile(r'^- B0([1-5]):\s*(.+)$', re.M)


def val(pattern, text):
    """Obtiene un valor de un informe o devuelve «No indicado»."""
    match = pattern.search(text)
    return match.group(1).strip() if match else 'No indicado'


def num(text):
    """Extrae el primer número decimal de un texto de rendimiento."""
    match = re.search(r'([0-9]+(?:[.,][0-9]+)?)', text.replace(',', '.'))
    return float(match.group(1)) if match else None


def parse(path):
    """Convierte un informe Markdown en un pequeño registro estadístico."""
    text = path.read_text(encoding='utf-8', errors='ignore')
    return {
        'file': path.name,
        'ram': val(RAM, text),
        'cpu': val(CPU, text),
        'os': val(OS, text),
        'gpu': val(GPU, text),
        'profile': val(PROFILE, text),
        'tok': num(val(TOK, text)),
        'result': val(RESULT, text) if 'RESULT' in globals() else 'No indicado',
        'b': dict(B.findall(text)),
    }


def bar(plt, counts, title, path, xlabel=''):
    """Guarda una gráfica de barras cuando existe al menos una categoría."""
    if not counts:
        return
    labels, values = zip(*counts.most_common())
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(labels, values)
    ax.set_title(title)
    ax.set_ylabel('Informes')
    ax.set_xlabel(xlabel)
    ax.tick_params(axis='x', rotation=35)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    """Lee informes reales y escribe un resumen reproducible."""
    ap = argparse.ArgumentParser(description='Estadísticas de la Manada LEONES')
    ap.add_argument('--input', default='results/manada')
    ap.add_argument('--output', default='results/manada/stats')
    args = ap.parse_args()

    root = Path(args.input)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    # Solo buscamos Markdown directamente dentro de results/manada. Los
    # ejemplos viven en results/manada/examples y quedan fuera deliberadamente.
    # README.md tampoco es un informe de participante.
    if root.exists():
        files = [p for p in sorted(root.glob('*.md')) if p.name.lower() != 'readme.md']
    else:
        files = []
    rs = [parse(p) for p in files]

    profiles = Counter(r['profile'] for r in rs)
    oses = Counter(r['os'] for r in rs)
    rams = Counter(r['ram'] for r in rs)
    cpus = Counter(r['cpu'] for r in rs)

    # Las estadísticas numéricas solo se calculan cuando hay informes reales.
    valid = [r for r in rs if r['tok'] is not None]
    passes = {}
    for i in range(1, 6):
        counter = Counter(r['b'].get(str(i), 'Pendiente') for r in rs)
        passes[f'B0{i}'] = sum(
            value for status, value in counter.items()
            if status.lower().startswith(('pass', 'ok', 'éxito', 'exito'))
        )

    if rs:
        # Importamos matplotlib solo cuando realmente necesitamos dibujar.
        plt = load_matplotlib()
        bar(plt, profiles, 'Manada — perfiles', out / 'profiles.png', 'Perfil')
        bar(plt, oses, 'Manada — sistemas operativos', out / 'os.png', 'Sistema')
        bar(plt, rams, 'Manada — RAM', out / 'ram.png', 'RAM')
        bar(plt, cpus, 'Manada — CPU', out / 'cpu.png', 'CPU')

        if valid:
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.scatter([r['profile'] for r in valid], [r['tok'] for r in valid])
            ax.axhline(10, linestyle='--')
            ax.set_title('Manada — rendimiento de inferencia')
            ax.set_ylabel('tok/s')
            ax.set_xlabel('Perfil')
            fig.tight_layout()
            fig.savefig(out / 'tokens-per-second.png', dpi=150)
            plt.close(fig)

        fig, ax = plt.subplots(figsize=(9, 5))
        ax.bar(list(passes), list(passes.values()))
        ax.set_title('Manada — PASS por Evaluación')
        ax.set_ylabel('Informes PASS')
        fig.tight_layout()
        fig.savefig(out / 'evaluacion-pass.png', dpi=150)
        plt.close(fig)

    # El README se genera incluso con cero informes. Así el workflow siempre
    # deja un artefacto explicativo y no necesita falsificar datos.
    md = [
        '# Estadísticas de la Manada',
        '',
        f'Informes analizados: **{len(rs)}**',
        '',
        '## Estado de datos',
        '',
        '- Los datos ficticios de `results/manada/examples/` no se incluyen en las estadísticas.',
        '- Un total de **0 informes** es un estado válido mientras no existan contribuciones reales.',
        '',
        '## Rendimiento',
        '',
        f'- Informes con tok/s: **{len(valid)}**',
        f'- Media tok/s: **{sum(r["tok"] for r in valid) / len(valid):.2f}**' if valid else '- Media tok/s: no disponible',
        f'- >=10 tok/s: **{sum(r["tok"] >= 10 for r in valid)}**' if valid else '- >=10 tok/s: no disponible',
        f'- >=100 tok/s: **{sum(r["tok"] >= 100 for r in valid)}**' if valid else '- >=100 tok/s: no disponible',
        '',
        '## Distribución',
        '',
    ]

    for title, counter in [('Perfiles', profiles), ('RAM', rams), ('Sistemas operativos', oses)]:
        md += [f'### {title}', '']
        md += [f'- {key}: {value}' for key, value in counter.most_common()]
        md += ['']

    md += ['## Evaluación — PASS', '']
    md += [f'- {key}: {value}' for key, value in passes.items()]
    md += ['', '## Señales para recomendaciones', '']

    for profile in sorted({r['profile'] for r in rs}):
        group = [r for r in rs if r['profile'] == profile]
        values = [x['tok'] for x in group if x['tok'] is not None]
        if values:
            md.append(
                f'- **{profile}**: media {sum(values) / len(values):.2f} tok/s; '
                f'{sum(x >= 10 for x in values)}/{len(values)} supera el mínimo de 10 tok/s.'
            )

    md += ['', '## Gráficas', '']
    if rs:
        md += [
            '- `profiles.png`', '- `os.png`', '- `ram.png`', '- `cpu.png`',
            '- `tokens-per-second.png`', '- `evaluacion-pass.png`'
        ]
    else:
        md.append('- No se generan gráficas hasta disponer de informes reales.')

    (out / 'README.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    print(f'Analizados: {len(rs)}; estadísticas: {out}/README.md')


if __name__ == '__main__':
    main()
