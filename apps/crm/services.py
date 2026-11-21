"""Lógica del CRM que no depende del admin.

La importación vive aquí y no en admin.py para poder probarla sin navegador y
reutilizarla después (por ejemplo, desde un comando o desde n8n).
"""

import csv
import io
from dataclasses import dataclass, field

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.utils import timezone

from core.utils import (
    InstagramInvalido, TelefonoInvalido, normalizar_correo, normalizar_encabezado, normalizar_instagram,
    normalizar_telefono,
)

from .models import Contacto, Etapa, Interaccion

COLUMNAS = ('empresa', 'contacto', 'telefono', 'correo', 'instagram', 'ciudad', 'rubro')

# Otros nombres habituales en hojas de cálculo que aceptamos como equivalentes.
ALIAS = {
    'nombre_contacto': 'contacto',
    'nombre': 'contacto',
    'celular': 'telefono',
    'tel': 'telefono',
    'email': 'correo',
    'e_mail': 'correo',
    'correo_electronico': 'correo',
    'ig': 'instagram',
}


class ErrorImportacion(Exception):
    """Problema con el archivo completo (no con una fila): se cancela todo."""


@dataclass
class ResultadoImportacion:
    importadas: list = field(default_factory=list)  # números de fila
    duplicadas: list = field(default_factory=list)  # (fila, motivo)
    errores: list = field(default_factory=list)     # (fila, motivo)


def leer_texto(archivo):
    datos = archivo.read()
    # Excel en español guarda "CSV UTF-8" con BOM, pero el "CSV (delimitado por
    # comas)" de siempre lo guarda en Windows-1252. utf-8-sig quita el BOM si
    # está; si el archivo no es UTF-8, se prueba Windows-1252.
    for codificacion in ('utf-8-sig', 'cp1252'):
        try:
            return datos.decode(codificacion)
        except UnicodeDecodeError:
            continue
    raise ErrorImportacion('No se pudo leer el archivo: guárdalo como "CSV UTF-8" desde Excel.')


def detectar_separador(texto):
    # Excel en español usa ";" (la "," es el separador decimal); otros programas usan ",".
    muestra = texto[:4096]
    try:
        return csv.Sniffer().sniff(muestra, delimiters=';,').delimiter
    except csv.Error:
        return ';' if muestra.count(';') >= muestra.count(',') else ','


def _leer_columnas(encabezados):
    columnas = [ALIAS.get(n, n) for n in map(normalizar_encabezado, encabezados)]
    if 'empresa' not in columnas:
        raise ErrorImportacion('Falta la columna "empresa" en la primera fila.')
    if 'telefono' not in columnas and 'correo' not in columnas:
        raise ErrorImportacion('El archivo necesita una columna "telefono" o "correo".')
    return columnas


@transaction.atomic
def importar_contactos_csv(archivo, asignar_a=None):
    """Crea un Contacto por cada fila válida y no duplicada del CSV.

    Las filas con problemas no detienen la importación: se apuntan en el
    resultado para mostrárselas al usuario.
    """
    texto = leer_texto(archivo)
    lector = csv.reader(io.StringIO(texto), delimiter=detectar_separador(texto))
    encabezados = next(lector, None)
    if not encabezados:
        raise ErrorImportacion('El archivo está vacío.')
    columnas = _leer_columnas(encabezados)

    # Teléfonos y correos que ya existen. Se cargan una vez en memoria para no
    # hacer una consulta por fila; luego se añaden los del propio archivo, así
    # también se detectan filas repetidas dentro del CSV.
    telefonos = set(Contacto.objects.exclude(telefono='').values_list('telefono', flat=True))
    correos = {c.lower() for c in Contacto.objects.exclude(correo='').values_list('correo', flat=True)}

    etapa_inicial = Etapa.objects.abiertas().first()
    resultado = ResultadoImportacion()
    nuevos = []

    # La fila 1 son los encabezados: la primera fila de datos es la 2, igual que en Excel.
    for numero, fila in enumerate(lector, start=2):
        if not any(celda.strip() for celda in fila):
            continue  # filas vacías al final del archivo

        datos = {col: '' for col in COLUMNAS}
        for posicion, columna in enumerate(columnas):
            if columna in datos and posicion < len(fila):
                datos[columna] = fila[posicion].strip()

        if not datos['empresa']:
            resultado.errores.append((numero, 'falta la empresa'))
            continue
        if not datos['telefono'] and not datos['correo']:
            resultado.errores.append((numero, 'necesita teléfono o correo'))
            continue
        try:
            telefono = normalizar_telefono(datos['telefono'])
        except TelefonoInvalido:
            resultado.errores.append((numero, f'teléfono no válido ({datos["telefono"]})'))
            continue
        correo = normalizar_correo(datos['correo'])
        try:
            instagram = normalizar_instagram(datos['instagram'])
        except InstagramInvalido:
            resultado.errores.append((numero, f'Instagram no válido ({datos["instagram"]})'))
            continue

        if telefono and telefono in telefonos:
            resultado.duplicadas.append((numero, f'el teléfono {telefono} ya existe'))
            continue
        if correo and correo in correos:
            resultado.duplicadas.append((numero, f'el correo {correo} ya existe'))
            continue

        contacto = Contacto(
            empresa=datos['empresa'],
            nombre_contacto=datos['contacto'],
            telefono=telefono,
            correo=correo,
            instagram=instagram,
            ciudad=datos['ciudad'],
            rubro=datos['rubro'],
            fuente=Contacto.Fuente.IMPORTACION,
            etapa=etapa_inicial,
            asignado_a=asignar_a,
        )
        # clean_fields valida formato de correo y largo máximo de cada campo,
        # igual que haría el formulario del admin.
        try:
            contacto.clean_fields(exclude=['etapa', 'asignado_a'])
        except ValidationError as error:
            motivo = '; '.join(f'{campo}: {" ".join(msgs)}' for campo, msgs in error.message_dict.items())
            resultado.errores.append((numero, motivo))
            continue

        if telefono:
            telefonos.add(telefono)
        if correo:
            correos.add(correo)
        nuevos.append(contacto)
        resultado.importadas.append(numero)

    # bulk_create inserta todas las filas en una sola consulta (mucho más
    # rápido que un save() por fila). No llama a save(), por eso arriba ya se
    # normalizó y se asignó la etapa a mano.
    try:
        Contacto.objects.bulk_create(nuevos)
    except IntegrityError:
        # Solo pasaría si otra persona crea el mismo contacto justo ahora.
        raise ErrorImportacion('Otro usuario creó contactos con los mismos datos mientras importabas. Vuelve a intentarlo.')
    return resultado


# --- Consultas para las listas y el dashboard ---------------------------------
# Aquí solo se calculan datos. Cómo se muestran (textos, colores, enlaces) lo
# deciden admin.py y core/dashboard.py.


def rango_de_hoy():
    """(inicio, fin) del día de hoy en hora de Colombia."""
    inicio = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    return inicio, inicio + timedelta(days=1)


def inicio_de_semana():
    """El lunes de esta semana a las 00:00 (hora de Colombia)."""
    inicio_hoy, _ = rango_de_hoy()
    return inicio_hoy - timedelta(days=inicio_hoy.weekday())


def contactos_de(usuario):
    """Los contactos que el usuario puede trabajar: todos o solo los suyos."""
    qs = Contacto.objects.all()
    if not usuario.is_superuser:
        qs = qs.filter(asignado_a=usuario)
    return qs


AGENDA_FILTROS = ('todas', 'vencidas', 'hoy')


def agenda_hoy(usuario, filtro='todas'):
    """Llamadas pendientes de hoy y vencidas (de días anteriores).

    "Vencida" = su día ya pasó. Una llamada de hoy a las 9:30 sigue siendo "de
    hoy" a las 11:00: todavía se puede hacer hoy.
    Se excluyen las etapas finales (Perdido): ya no se llaman.
    """
    inicio, fin = rango_de_hoy()
    pendientes = (
        contactos_de(usuario)
        .exclude(etapa__es_final=True)
        .filter(proxima_llamada__lt=fin)
        .select_related('etapa', 'asignado_a')
        .order_by('proxima_llamada', 'empresa')
    )
    vencidas = pendientes.filter(proxima_llamada__lt=inicio)
    de_hoy = pendientes.filter(proxima_llamada__gte=inicio)
    elegidas = {'vencidas': vencidas, 'hoy': de_hoy}.get(filtro, pendientes)
    return {
        'filtro': filtro if filtro in AGENDA_FILTROS else 'todas',
        'contactos': list(elegidas),
        'total': pendientes.count(),
        'vencidas': vencidas.count(),
        'hoy': de_hoy.count(),
    }


def contar_para_hoy(queryset):
    """Cuántos contactos de este queryset tienen llamada programada hoy."""
    inicio, fin = rango_de_hoy()
    return queryset.filter(proxima_llamada__gte=inicio, proxima_llamada__lt=fin).count()


def embudo():
    """Cuántas empresas hay en cada etapa (sin las finales), en orden.

    Ojo: es una FOTO de hoy, no una tasa de conversión. Que haya 52 en
    Contactado y 148 en Por llamar no significa que el 35 % "pase": son
    empresas distintas en momentos distintos.
    """
    etapas = list(
        Etapa.objects.exclude(es_final=True)
        .annotate(total=Count('contactos'))
        .order_by('orden', 'nombre')
    )
    total_empresas = Contacto.objects.count()
    maximo = max((e.total for e in etapas), default=0) or 1
    filas = []
    anterior = None
    for etapa in etapas:
        filas.append({
            'etapa': etapa,
            'total': etapa.total,
            'ancho': round(etapa.total * 100 / maximo),
            'de_total': round(etapa.total * 100 / total_empresas) if total_empresas else 0,
            'anterior': anterior,
            'de_anterior': round(etapa.total * 100 / anterior.total) if anterior and anterior.total else None,
        })
        anterior = etapa
    return {'filas': filas, 'total_empresas': total_empresas}


def llamadas_de_la_semana(usuario=None):
    """Llamadas desde el lunes, agrupadas por quien las hizo.

    Con usuario: solo las suyas (vista del vendedor). Sin usuario: todo el equipo.
    Count(..., filter=...) cuenta en la misma consulta cuántas cumplen cada condición.
    """
    qs = Interaccion.objects.filter(fecha__gte=inicio_de_semana(), usuario__isnull=False)
    if usuario is not None:
        qs = qs.filter(usuario=usuario)
    filas = (
        qs.values('usuario', 'usuario__first_name', 'usuario__last_name', 'usuario__username')
        .annotate(
            total=Count('id'),
            contestaron=Count('id', filter=Q(resultado__in=Interaccion.CONTESTARON)),
            interesados=Count('id', filter=Q(resultado=Interaccion.Resultado.INTERESADO)),
        )
        # order_by reemplaza el orden por fecha del modelo; si no, Django
        # agruparía también por fecha y saldría una fila por llamada.
        .order_by('-total')
    )
    return list(filas)
