"""EJEMPLO: datos de finanzas inventados para el dashboard.

Finanzas (cobros, pagos, gastos) se construye en la fase 3. Mientras tanto,
estos números permiten ver y probar el diseño. Son los del boceto.

Cuando exista apps/finanzas, cada función de aquí se reemplaza por una
consulta real en apps/finanzas/services.py y este archivo se borra.
"""

import json

from core.utils import pesos

MES = 'Noviembre 2026'


def tarjetas():
    # tono: cómo se colorea el valor (normal, exito, primario, alerta).
    return [
        {'titulo': 'Ingresos cobrados', 'valor': pesos(8_450_000), 'detalle': '5 pagos recibidos', 'tono': 'normal'},
        {'titulo': 'Egresos pagados', 'valor': pesos(2_130_000), 'detalle': 'Fijos y gastos sueltos', 'tono': 'normal'},
        {'titulo': 'Utilidad', 'valor': pesos(6_320_000), 'detalle': 'Margen del 75 %', 'tono': 'exito'},
        {'titulo': 'Ingreso recurrente mensual', 'valor': pesos(3_600_000), 'detalle': '12 planes activos', 'tono': 'primario'},
        {'titulo': 'Total que me deben', 'valor': pesos(5_650_000), 'detalle': f'{pesos(1_700_000)} ya vencido', 'tono': 'alerta'},
    ]


def grafico_seis_meses():
    """JSON para el gráfico de barras de unfold (Chart.js).

    Los colores usan variables CSS de unfold: el gráfico respeta la marca y el
    modo oscuro sin escribir colores fijos.
    """
    # unfold dibuja por defecto barras finas (4 px) y superpuestas. Estas
    # opciones, puestas en cada serie, las dejan anchas y lado a lado, como en
    # el diseño, sin reemplazar la configuración del gráfico de unfold.
    barras = {'grouped': True, 'maxBarThickness': 28, 'barPercentage': 0.8, 'categoryPercentage': 0.6, 'borderRadius': 4}
    return json.dumps({
        'labels': ['Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov'],
        'datasets': [
            {
                'label': 'Ingresos',
                'data': [4_100_000, 5_000_000, 4_700_000, 6_300_000, 7_400_000, 8_450_000],
                'backgroundColor': 'var(--color-primary-600)',
                **barras,
            },
            {
                'label': 'Egresos',
                'data': [1_600_000, 1_900_000, 2_400_000, 2_000_000, 2_200_000, 2_130_000],
                'backgroundColor': 'var(--color-base-800)',
                **barras,
            },
        ],
    })


def esta_semana():
    return {
        'por_recibir': {
            'total': pesos(2_150_000),
            'filas': [
                {'nombre': 'Rebel Chef', 'detalle': 'Plan mensual WhatsApp · vie 20 nov', 'valor': pesos(350_000)},
                {'nombre': 'La Cremosa', 'detalle': 'Anticipo menú web · sáb 21 nov', 'valor': pesos(600_000)},
                {'nombre': 'Binco Store', 'detalle': 'Cuota 2 de 3 · dom 22 nov', 'valor': pesos(1_200_000)},
            ],
        },
        'por_pagar': {
            'total': pesos(1_360_000),
            'filas': [
                {'nombre': 'Meta Ads', 'detalle': 'Pauta noviembre · vie 20 nov', 'valor': pesos(1_200_000)},
                {'nombre': 'Herramientas', 'detalle': 'n8n y Google Workspace · dom 22 nov', 'valor': pesos(160_000)},
            ],
        },
    }


def cobros_vencidos():
    filas = [
        {'cliente': 'Auto Direct', 'concepto': 'Plan mensual WhatsApp · octubre', 'valor': pesos(350_000), 'vencio': '25 oct 2026', 'dias': 24},
        {'cliente': 'Chancho Brasas', 'concepto': 'Saldo menú QR por mesa', 'valor': pesos(900_000), 'vencio': '8 nov 2026', 'dias': 10},
        {'cliente': 'Alpha Gainz Gang', 'concepto': 'Mantenimiento tienda Shopify', 'valor': pesos(450_000), 'vencio': '13 nov 2026', 'dias': 5},
    ]
    return {'filas': filas, 'resumen': f'3 cobros · {pesos(1_700_000)} en mora'}


def datos():
    return {
        'es_ejemplo': True,
        'mes': MES,
        'tarjetas': tarjetas(),
        'grafico': grafico_seis_meses(),
        'semana': esta_semana(),
        'vencidos': cobros_vencidos(),
        # "Marcar pagado" queda visible pero desactivado hasta la fase 3.
        'boton_desactivado': {'disabled': True, 'title': 'Disponible cuando exista Finanzas (fase 3)'},
    }
