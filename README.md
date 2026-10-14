# Website Form to Telegram — Odoo 18.0

Reenvía **todos los formularios del website de Odoo** (contacto y cualquier form del Form Builder) a un **chat, grupo o canal de Telegram** vía Bot API, en tiempo real y sin romper el flujo original.

> Si Telegram falla, el formulario sigue respondiendo éxito. Nunca bloquea al visitante.

[![Odoo](https://img.shields.io/badge/Odoo-18.0-714B67?style=flat-square&logo=odoo)](https://www.odoo.com)
[![License](https://img.shields.io/badge/License-LGPL--3-blue?style=flat-square)](LICENSE)
[![Telegram](https://img.shields.io/badge/Telegram-Bot_API-26A5E4?style=flat-square&logo=telegram)](https://core.telegram.org/bots/api)

---

## ✨ Features

- 📨 Intercepta `WebsiteForm.insert_record()` → cubre **todos** los modelos del Form Builder (`mail.mail`, `crm.lead`, modelos custom, etc.).
- ⚙️ Config global simple: `bot token` + `chat ID` en **Ajustes** (con botón *Enviar mensaje de prueba*).
- 🧹 Convierte HTML a texto plano legible (`<br>`, `<p>`, `<div>`, `<li>` → saltos de línea / guiones).
- ✂️ Respeta el límite de Telegram (**4096 caracteres**): divide en chunks por saltos de línea, con corte duro si una línea sola lo supera.
- 🛡️ *Fail-safe*: todo el envío está envuelto en `try/except` + logueo; jamás lanza excepción al visitante.
- 📍 **Captura el origen del anuncio** (UTM + `gclid`/`fbclid`): los guarda en cookies al cargar la landing y los anexa al mail y a Telegram en cada formulario.
- 🧪 Tests incluidos (`TransactionCase` + mock de `requests.post`).

## 📍 Captura de UTM / origen del anuncio

Los links de los anuncios traen UTMs (`?utm_source=facebook&utm_medium=cpc&utm_campaign=promo...`). Este módulo los captura **server-side, sin tocar el formulario**:

1. **Al cargar cualquier página** (`models/ir_http.py`, mismo mecanismo que el módulo `utm` de Odoo), si la URL trae `utm_source`, `utm_medium`, `utm_campaign`, `utm_content`, `utm_term`, `gclid` o `fbclid`, se guardan en **cookies propias** (`wft_utm_source`, etc.) por **31 días**. Así el origen sobrevive aunque el visitante navegue y envíe el formulario días después.
2. **Al enviar el formulario** (`controllers/main.py`), se leen esas cookies (con fallback a las nativas `odoo_utm_*` de Odoo) y se anexa un bloque a los datos del formulario:

```
— Origen (UTM) —
utm_source: facebook
utm_medium: cpc
utm_campaign: promo-octubre
utm_content: video-a
gclid: EAIaIQ...
```

3. Ese bloque queda **persistido en el registro** (en `mail.mail` va dentro del `body_html`, o sea que **llega en el mail**) y **también sale en Telegram**.
4. Si el formulario apunta a `crm.lead`, Odoo además completa los campos nativos *Campaña / Origen / Medio* del lead (`utm.mixin`); este módulo no interfiere con eso.

> Nota: Odoo de forma nativa solo persiste en cookie `utm_campaign/source/medium`. Los demás (`utm_content`, `utm_term`, `gclid`, `fbclid`) los persiste este módulo; sin él se perderían al navegar.

## 📋 Requisitos

| Requisito | Versión |
|-----------|---------|
| Odoo | 18.0 |
| Módulos | `base`, `mail`, `website`, `utm` |
| Python | `requests` (ya es dependencia de Odoo) |
| Telegram | Un bot creado con [@BotFather](https://t.me/BotFather) |

## 📦 Instalación

### Opción A — como addon suelto

```bash
# 1. Clonar dentro de tu carpeta de addons
git clone -b 18.0 git@github.com:Alitux/website_form_telegram.git

# 2. Reiniciar Odoo y actualizar lista de aplicaciones
# 3. Instalar "Website Form to Telegram"
```

### Opción B — estructura multi-addon

Si tu `odoo.conf` usa un `addons_path` custom:

```ini
addons_path = /ruta/a/odoo/addons,/ruta/a/tus/addons
```

Copiá la carpeta `website_form_telegram/` dentro de `/ruta/a/tus/addons`, reiniciá Odoo con `-u website_form_telegram` o instalá desde Apps.

## ⚙️ Configuración

### 1. Crear el bot

1. Hablá con [@BotFather](https://t.me/BotFather) en Telegram → `/newbot` → te da el **Bot Token** (ej: `123456:ABC-DEF...`).
2. Agregá el bot a tu grupo/canal (para canales, debe ser **administrador**).

### 2. Obtener el Chat ID

- **Chat 1-a-1 / grupo:** escribile al bot y luego consultá `https://api.telegram.org/bot<TU_TOKEN>/getUpdates`. El `chat.id` es tu ID.
  - Alternativa fácil: usar [@userinfobot](https://t.me/userinfobot) o [@getmyid_bot](https://t.me/getmyid_bot).
- **Grupo:** suele ser negativo, ej: `-123456789`.
- **Supergrupo / canal:** formato `-100xxxxxxxxxx`, ej: `-1001234567890`.

### 3. Configurar en Odoo

`Ajustes → Telegram → Formularios web a Telegram`:

| Campo | `ir.config_parameter` | Ejemplo |
|-------|----------------------|---------|
| ✅ Habilitado | `website_form_telegram.enabled` | `True` |
| Bot Token | `website_form_telegram.bot_token` | `123456:ABC...` |
| Chat ID | `website_form_telegram.chat_id` | `-1001234567890` |

O por shell/CSV de parámetros del sistema. Luego pulsá **Enviar mensaje de prueba** → deberías recibir `🔔 Test OK...` en Telegram.

## 💬 Qué mensaje llega

**Caso típico (formulario de contacto → `mail.mail`):**

```
🔔 Nuevo formulario: Correo electrónico
📌 Asunto: Contacto web: Presupuesto

— Datos del formulario —
...

— Cuerpo completo —
Nombre: Juan
Email: juan@mail.com
...
```

**Caso genérico (otro modelo):**

```
🔔 Nuevo formulario: Contact
name: Juan
email: j@x.com
phone: 123...

— Otros datos —
...
```

- Campos principales (`subject`, `name`, `email`, `phone`, ...) van primero.
- Se filtra `website_form_signature` y claves internas (`_...`, `context`, `bytes`).
- Valores largos se truncan (`1000` por campo, `2000` custom, `15000` total) y luego se *chunkea* a 4096 en el envío.

## 🗂️ Estructura

```
website_form_telegram/
├── __init__.py                  # importa controllers + models
├── __manifest__.py              # manifiesto v18.0.1.1.0
├── controllers/
│   └── main.py                  # WebsiteFormTelegram: inyecta UTM + notifica Telegram
├── models/
│   ├── ir_http.py               # persiste UTM/gclid/fbclid de la URL en cookies wft_*
│   ├── telegram_service.py      # config, html_to_text, split, send, build + tracking
│   └── res_config_settings.py   # settings + botón de test
├── views/
│   └── res_config_settings_views.xml
├── security/
│   └── ir.model.access.csv
├── tests/
│   └── test_telegram.py
└── README.md
```

### Diseño

- `controllers/main.py` — *override* no intrusivo: llama a `super()`, y **después** notifica. Si no hay config o falla algo, retorna `record_id` igual.
- `models/telegram_service.py` — `website_form_telegram.service` (`AbstractModel`, sin ACL necesaria):
  - `_get_config()` → lee `ir.config_parameter`.
  - `html_to_text()` → regex + `html.unescape`.
  - `_split_message()` → chunks ≤ 4096.
  - `send_message()` → `POST https://api.telegram.org/bot<token>/sendMessage`, nunca lanza.
  - `build_form_message()` → arma texto para modelos no-`mail.mail`.

## 🧪 Tests

```bash
# Correr solo este módulo (ejemplo con entrypoint típico)
odoo -c odoo.conf -d testdb --test-tags website_form_telegram --stop-after-init -u website_form_telegram
```

Cobertura actual (`tests/test_telegram.py`):

- `html_to_text` convierte `<p>Hola<br/>Mundo</p>` → `Hola\nMundo`.
- `_split_message` divide 5000 chars en 2 chunks ≤ 4096.
- `build_form_message` incluye valores y custom.
- `send_message` sin config → `False` sin excepción.
- `send_message` con config + mock → `True` y un solo `POST`.
- `get_tracking` lee cookies propias `wft_*` y hace fallback a `odoo_utm_*`.
- `format_tracking_block` arma el bloque `— Origen (UTM) —` (vacío si no hay datos).

## 🔧 Troubleshooting

| Síntoma | Causa probable | Fix |
|---------|---------------|-----|
| No llega nada, sin error visible | Módulo deshabilitado o token/chat vacío | Revisá Ajustes → Telegram; mirá el log: `Telegram: sin token/chat configurado` |
| `Telegram API error 400` | Chat ID mal / bot no miembro | Verificá el ID (grupos `-100...`), agregá el bot al grupo/canal como admin |
| `Telegram API error 401` | Token inválido | Regenerá con `@BotFather` |
| `Telegram: fallo de conexión` | Sin salida a internet / timeout | Revisá firewall/proxy; timeout es 10s por chunk |
| Mensaje cortado | Normal | Se divide en múltiples mensajes de ≤ 4096 |
| No aparece el bloque UTM | Visitante sin cookies (entró directo, sin pasar por la URL con parámetros) o cookies vencidas/bloqueadas | Probá entrando a la landing con `?utm_source=test` y luego enviá el form; revisá cookies `wft_*` en el navegador |

Logs útiles:

```bash
tail -f odoo.log | grep -i telegram
```

## 🔒 Seguridad

- El token se guarda como `ir.config_parameter` y el campo en Ajustes usa `password="True"`.
- No se loguea el token; solo status code + primeros 500 chars de la respuesta en caso de error.
- Solo se envía texto plano (se *strippean* tags HTML).

## 🗺️ Roadmap / ideas

- [ ] Soporte de formato Markdown/HTML parse mode opcional.
- [ ] Mapeo de plantillas por modelo de formulario.
- [ ] Cola con reintentos (`queue_job`) en vez de envío sincrónico.
- [ ] Múltiples destinos por formulario.

PRs y issues bienvenidos.

## 📄 Licencia

[LGPL-3](https://www.gnu.org/licenses/lgpl-3.0.html).

## ✍️ Autor

**Alitux** — [alitux.com.ar](https://alitux.com.ar)

Repo: `git@github.com:Alitux/website_form_telegram.git` (rama `18.0`)
