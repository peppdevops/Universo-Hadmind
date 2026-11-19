# Bitácora automática con n8n

Cada **lunes a las 7:00 a. m.** (hora de Colombia) n8n:

1. Pregunta a la app qué noticias ya se usaron, para no repetirlas.
2. Lee los RSS de 6 medios: Xataka, Hipertextual, WWWhat's new, ENTER.CO, Impacto TIC y Portafolio.
3. **OpenAI** elige la noticia más útil para pymes.
4. Descarga el texto completo de esa noticia.
5. **OpenAI** escribe un artículo original en español.
6. **OpenAI** genera la imagen. El estilo HADMIND es fijo y la IA solo describe la escena.
7. Envía todo a la app como **borrador**.
8. Envía el correo a hadmind@gmail.com con el botón **Revisar y publicar**.

Si algo falla, el flujo de avisos manda un correo que dice en qué paso falló.

| Archivo | Qué es |
|---|---|
| `bitacora_semanal.json` | El flujo principal |
| `bitacora_errores.json` | Avisa por correo si el flujo principal falla |

Lo que normalmente se cambia (medios, modelos, estilo de imagen, dirección de la app) está en el
primer nodo, **Configuración**.

---

## 1. Antes de empezar

- **OpenAI.** Necesitas una clave de API (platform.openai.com → API keys).
  - Pon un **límite de gasto mensual** en Billing → Limits. El costo es de un texto y una imagen por semana.
  - El modelo de imagen `gpt-image-1` exige **verificar la organización** (Settings → Organization → Verify).
    Si no está verificada, el paso "Generar imagen (IA)" falla con un error 403.
- **Gmail.** Necesitas una **contraseña de aplicación** de hadmind@gmail.com:
  1. Cuenta de Google → Seguridad → activa la **Verificación en 2 pasos**.
  2. Busca **Contraseñas de aplicaciones**, crea una llamada `n8n` y copia los 16 caracteres.
     Esa clave solo sirve para enviar correo: no da acceso a la cuenta.

## 2. Probar en tu PC (no expone nada a internet)

1. Django debe estar encendido (`docker compose up`) y el `.env` debe tener:
   ```
   DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,host.docker.internal
   N8N_API_TOKEN=<la clave>
   SITIO_URL=http://localhost:8000
   ```
2. Arranca un n8n de prueba. Usa la **misma versión que el VPS**: en el VPS, ejecuta
   `docker exec <contenedor-n8n> n8n --version` y cambia `2.48.6` por esa versión.
   ```
   docker run -it --rm --name n8n_local -p 5678:5678 -v n8n_local:/home/node/.n8n -e GENERIC_TIMEZONE=America/Bogota docker.n8n.io/n8nio/n8n:2.48.6
   ```
   Abre http://localhost:5678 y crea un usuario. Es solo para tu PC.
3. **Importa los dos flujos:** Overview → botón ⋯ → *Import from File*.
4. **Crea las 3 credenciales.** En cada nodo marcado abajo, elígela en el campo *Credential*.

   | Credencial | Tipo | Datos | Nodos |
   |---|---|---|---|
   | Hadmind API | Header Auth | Name: `Authorization` · Value: `Bearer <N8N_API_TOKEN>` | Fuentes usadas, Enviar a la app |
   | OpenAI | OpenAI | API Key | Elegir noticia (IA), Escribir artículo (IA), Generar imagen (IA) |
   | Gmail SMTP | SMTP | User: `hadmind@gmail.com` · Password: la contraseña de aplicación · Host: `smtp.gmail.com` · Port: `465` · SSL/TLS: activado | Correo de aprobación, Avisar por correo |

5. Conecta el aviso de errores. Abre "Bitácora semanal" → ⋯ → *Settings* → *Error workflow* → elige
   "Bitácora: aviso de errores". Guarda.
6. Pulsa **Execute workflow**. Tarda de 1 a 3 minutos, sobre todo por la imagen.
7. Revisa el correo y pulsa **Revisar y publicar**. En la prueba local, la imagen del correo no se ve
   porque Gmail no puede llegar a tu PC. Es normal: en la página de revisión sí aparece.

## 3. En el VPS (el día del lanzamiento)

1. En `/opt/hadmind-web/.env`:
   ```
   N8N_API_TOKEN=<una clave NUEVA, distinta a la de tu PC>
   SITIO_URL=https://hadmind.com.co
   ```
   Para generar la clave: `python3 -c "import secrets; print(secrets.token_urlsafe(40))"`
2. Crea la carpeta de imágenes: `mkdir -p /opt/hadmind-web/media`.
3. Aplica los cambios de Nginx de `despliegue/nginx-hadmind.conf`.
4. En https://n8n.hadmind.tech:
   - importa los dos flujos;
   - crea las 3 credenciales, con la clave **nueva** en "Hadmind API";
   - en **Configuración**, cambia `url_app` a `https://hadmind.com.co`;
   - conecta el aviso de errores (paso 2.5).
5. Prueba una vez con **Execute workflow**. Si todo sale bien, **activa** el flujo (interruptor o
   botón *Publish*, arriba a la derecha). Desde ahí corre solo cada lunes.

### Asegurar n8n

Hoy n8n está publicado en `0.0.0.0:5678`: cualquiera puede entrar por `http://IP-del-VPS:5678`,
sin https y sin pasar por Nginx. En el docker compose de n8n:

```yaml
ports:
  - "127.0.0.1:5678:5678"     # solo Nginx (n8n.hadmind.tech) puede llegar
image: docker.n8n.io/n8nio/n8n:2.48.6   # versión fija en vez de "latest"
```

Después, `docker compose up -d` y comprueba que https://n8n.hadmind.tech sigue abriendo y que
`http://IP:5678` ya no responde.
