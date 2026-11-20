/*
 * Formulario de contacto (temporal): mientras no exista el modelo Lead del CRM,
 * al enviar se abre WhatsApp con la consulta ya redactada.
 */
(function () {
    const form = document.querySelector('[data-form-contacto]');
    if (!form) return;
    const panel = document.querySelector('[data-form-panel]');
    const enviado = document.querySelector('[data-form-enviado]');
    const nombre = document.querySelector('[data-form-nombre]');
    const otra = document.querySelector('[data-form-otra]');

    function mensaje(d) {
        const lineas = [
            'Hola HADMIND, quiero hacer una consulta.',
            '',
            `Motivo: ${d.get('motivo')}`,
            `Nombre: ${d.get('nombre')} ${d.get('apellido')}`,
            `Correo: ${d.get('correo')}`,
            `Teléfono: ${d.get('telefono')}`,
            `Empresa: ${d.get('empresa')}${d.get('cargo') ? ` (${d.get('cargo')})` : ''}`,
            `Ubicación: ${d.get('ubicacion')}${d.get('ciudad') ? `, ${d.get('ciudad')}` : ''}`,
            `Nos conoció por: ${d.get('origen')}`,
            '',
            'Consulta:',
            d.get('consulta'),
        ];
        return lineas.join('\n');
    }

    // El evento submit solo llega si el navegador ya validó los campos obligatorios
    form.addEventListener('submit', (ev) => {
        ev.preventDefault();
        const datos = new FormData(form);
        const url = `${form.dataset.whatsapp}?text=${encodeURIComponent(mensaje(datos))}`;
        window.open(url, '_blank', 'noopener');

        nombre.textContent = datos.get('nombre');
        panel.hidden = true;
        enviado.hidden = false;
        enviado.scrollIntoView({ block: 'center' });
    });

    otra.addEventListener('click', () => {
        form.reset();
        enviado.hidden = true;
        panel.hidden = false;
        form.querySelector('select, input').focus();
    });
})();
