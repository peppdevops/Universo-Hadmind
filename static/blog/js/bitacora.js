/*
 * La Bitácora: ventana con el resto de la noticia sin salir de la página.
 * - Con ratón: al dejarlo ~0,3 s sobre una tarjeta se abre al lado (a la
 *   derecha o, si no cabe, a la izquierda) y se cierra al salir. Se puede
 *   pasar el ratón a la ventana para leer y desplazar el texto.
 * - Con el dedo: un toque abre la ventana desde abajo, con X para cerrar.
 *   Para ir a la página del artículo está "Leer en su página".
 * - Teclado: Enter sigue el enlace normal; Esc cierra la ventana.
 * Una sola ventana para todas las tarjetas: si estuviera dentro de cada una,
 * el efecto de "subir" la tarjeta (transform) desplazaría su position: fixed.
 */
(function () {
    const ventana = document.querySelector('[data-bitacora-ventana]');
    const fondo = document.querySelector('[data-bitacora-fondo]');
    const tarjetas = document.querySelectorAll('[data-bitacora-tarjeta]');
    if (!ventana || !fondo || !tarjetas.length) return;

    const cuerpo = ventana.querySelector('[data-bitacora-ventana-cuerpo]');
    const botonCerrar = ventana.querySelector('[data-bitacora-cerrar]');

    const ESPERA_ABRIR = 300;   // ms con el ratón encima antes de abrir
    const ESPERA_CERRAR = 180;  // ms de margen para pasar de la tarjeta a la ventana
    const MARGEN = 16;          // distancia mínima al borde de la pantalla
    const SEPARACION = 14;      // espacio entre tarjeta y ventana

    // Al <body> para que nada de la sección (overflow, transform) la recorte
    document.body.append(fondo, ventana);

    let actual = null;          // tarjeta abierta
    let modo = null;            // 'flotante' (ratón) u 'hoja' (táctil)
    let temporizadorAbrir = null;
    let temporizadorCerrar = null;
    let temporizadorOcultar = null;
    let ultimoPuntero = '';     // tipo del último pointerdown: mouse, touch o pen
    let focoAnterior = null;

    function abrir(tarjeta, nuevoModo) {
        clearTimeout(temporizadorCerrar);
        clearTimeout(temporizadorOcultar);
        if (actual === tarjeta && modo === nuevoModo) return;
        if (actual) actual.classList.remove('es-activa');

        actual = tarjeta;
        modo = nuevoModo;
        tarjeta.classList.add('es-activa');

        const contenido = tarjeta.querySelector('[data-bitacora-contenido]').content.cloneNode(true);
        contenido.querySelector('[data-bitacora-titulo]').id = 'bitacora-ventana-titulo';
        cuerpo.replaceChildren(contenido);
        cuerpo.scrollTop = 0;

        const esHoja = modo === 'hoja';
        ventana.classList.toggle('bitacora-ventana--hoja', esHoja);
        ventana.classList.toggle('bitacora-ventana--flotante', !esHoja);
        ventana.style.left = ventana.style.top = '';
        if (esHoja) ventana.setAttribute('aria-modal', 'true');
        else ventana.removeAttribute('aria-modal');
        ventana.hidden = false;
        fondo.hidden = !esHoja;

        if (esHoja) {
            // Mientras la hoja está abierta la página de atrás no se mueve
            document.documentElement.style.overflow = 'hidden';
            focoAnterior = document.activeElement;
            botonCerrar.focus({ preventScroll: true });
        } else {
            colocar();
        }
        // Un fotograma después para que se vea la transición de entrada
        requestAnimationFrame(() => {
            ventana.classList.add('es-visible');
            fondo.classList.add('es-visible');
        });
    }

    function cerrar() {
        clearTimeout(temporizadorAbrir);
        clearTimeout(temporizadorCerrar);
        if (!actual) return;
        const eraHoja = modo === 'hoja';
        actual.classList.remove('es-activa');
        actual = null;
        modo = null;
        ventana.classList.remove('es-visible');
        fondo.classList.remove('es-visible');
        document.documentElement.style.overflow = '';
        temporizadorOcultar = setTimeout(() => {
            ventana.hidden = true;
            fondo.hidden = true;
            cuerpo.replaceChildren();
        }, 280);
        if (eraHoja && focoAnterior) focoAnterior.focus({ preventScroll: true });
        focoAnterior = null;
    }

    function programarCierre() {
        clearTimeout(temporizadorAbrir);
        clearTimeout(temporizadorCerrar);
        temporizadorCerrar = setTimeout(cerrar, ESPERA_CERRAR);
    }

    // Pone la ventana junto a la tarjeta, siempre dentro de la pantalla
    function colocar() {
        if (!actual || modo !== 'flotante') return;
        const r = actual.getBoundingClientRect();
        const anchoPantalla = document.documentElement.clientWidth;
        const altoPantalla = window.innerHeight;

        // La tarjeta salió de la pantalla al hacer scroll: se cierra
        if (r.bottom < 0 || r.top > altoPantalla) {
            cerrar();
            return;
        }

        const ancho = ventana.offsetWidth;
        const alto = ventana.offsetHeight;
        const limitar = (v, min, max) => Math.max(min, Math.min(v, max));

        let izquierda;
        if (r.right + SEPARACION + ancho <= anchoPantalla - MARGEN) {
            izquierda = r.right + SEPARACION;              // a la derecha
        } else if (r.left - SEPARACION - ancho >= MARGEN) {
            izquierda = r.left - SEPARACION - ancho;       // a la izquierda
        } else {
            // Pantalla estrecha: centrada sobre la tarjeta
            izquierda = limitar(r.left + (r.width - ancho) / 2, MARGEN, anchoPantalla - ancho - MARGEN);
        }
        const arriba = limitar(r.top, MARGEN, altoPantalla - alto - MARGEN);

        ventana.style.left = `${Math.round(izquierda)}px`;
        ventana.style.top = `${Math.round(arriba)}px`;
    }

    tarjetas.forEach((tarjeta) => {
        const enlace = tarjeta.querySelector('a');

        tarjeta.addEventListener('pointerenter', (e) => {
            if (e.pointerType !== 'mouse') return;
            clearTimeout(temporizadorCerrar);
            clearTimeout(temporizadorAbrir);
            // Si ya hay una abierta se cambia sin esperar
            const espera = actual && modo === 'flotante' ? 0 : ESPERA_ABRIR;
            temporizadorAbrir = setTimeout(() => abrir(tarjeta, 'flotante'), espera);
        });
        tarjeta.addEventListener('pointerleave', (e) => {
            if (e.pointerType === 'mouse') programarCierre();
        });

        enlace.addEventListener('pointerdown', (e) => { ultimoPuntero = e.pointerType; });
        enlace.addEventListener('click', (e) => {
            const tactil = ultimoPuntero === 'touch' || ultimoPuntero === 'pen';
            ultimoPuntero = '';
            if (!tactil) return; // ratón o teclado: va a la página del artículo
            e.preventDefault();
            abrir(tarjeta, 'hoja');
        });
    });

    ventana.addEventListener('pointerenter', (e) => {
        if (e.pointerType === 'mouse') clearTimeout(temporizadorCerrar);
    });
    ventana.addEventListener('pointerleave', (e) => {
        if (e.pointerType === 'mouse' && modo === 'flotante') programarCierre();
    });

    botonCerrar.addEventListener('click', cerrar);
    fondo.addEventListener('click', cerrar);
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && actual) cerrar();
    });

    // La tarjeta se mueve con el scroll: la ventana la sigue
    let pendiente = false;
    window.addEventListener('scroll', () => {
        if (pendiente || modo !== 'flotante') return;
        pendiente = true;
        requestAnimationFrame(() => { pendiente = false; colocar(); });
    }, { passive: true });
    window.addEventListener('resize', () => { if (modo === 'flotante') cerrar(); });
})();
