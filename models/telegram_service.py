# -*- coding: utf-8 -*-
import html
import logging
import re

from odoo import api, models

_logger = logging.getLogger(__name__)

PARAM_ENABLED = 'website_form_telegram.enabled'
PARAM_TOKEN = 'website_form_telegram.bot_token'
PARAM_CHAT = 'website_form_telegram.chat_id'

TELEGRAM_LIMIT = 4096


class TelegramService(models.AbstractModel):
    _name = 'website_form_telegram.service'
    _description = 'Website Form Telegram Notifier'

    @api.model
    def _get_config(self):
        ICP = self.env['ir.config_parameter'].sudo()
        return {
            'enabled': ICP.get_param(PARAM_ENABLED, 'False') == 'True',
            'bot_token': (ICP.get_param(PARAM_TOKEN, '') or '').strip(),
            'chat_id': (ICP.get_param(PARAM_CHAT, '') or '').strip(),
        }

    @api.model
    def html_to_text(self, value):
        """Convierte HTML a texto plano legible para Telegram."""
        if not value:
            return ''
        text = str(value)
        # <br> y </p> -> saltos de línea
        text = re.sub(r'<\s*br\s*/?\s*>', '\n', text, flags=re.I)
        text = re.sub(r'</\s*p\s*>', '\n', text, flags=re.I)
        text = re.sub(r'</\s*div\s*>', '\n', text, flags=re.I)
        text = re.sub(r'</\s*li\s*>', '\n', text, flags=re.I)
        text = re.sub(r'<li[^>]*>', '- ', text, flags=re.I)
        # strip tags
        text = re.sub(r'<[^>]+>', '', text)
        text = html.unescape(text)
        # normalizar espacios sin borrar saltos
        lines = [re.sub(r'[ \t]+', ' ', ln).strip() for ln in text.splitlines()]
        # quitar líneas vacías duplicadas
        clean = []
        for ln in lines:
            if ln or (clean and clean[-1] != ''):
                clean.append(ln)
        return '\n'.join(clean).strip()

    @api.model
    def _split_message(self, text):
        """Divide el mensaje en chunks <= 4096 respetando saltos de línea."""
        text = text or ''
        if len(text) <= TELEGRAM_LIMIT:
            return [text]
        chunks, current = [], []
        current_len = 0
        for line in text.splitlines(keepends=True):
            if current_len + len(line) > TELEGRAM_LIMIT and current:
                chunks.append(''.join(current))
                current, current_len = [], 0
            # línea individual más larga que el límite: corte duro
            while len(line) > TELEGRAM_LIMIT:
                chunks.append(line[:TELEGRAM_LIMIT])
                line = line[TELEGRAM_LIMIT:]
            current.append(line)
            current_len += len(line)
        if current:
            chunks.append(''.join(current))
        return chunks or ['']

    @api.model
    def send_message(self, text, chat_id=None, bot_token=None):
        """Envía texto a Telegram. Devuelve True si OK. Nunca lanza excepción."""
        import requests

        config = self._get_config()
        token = (bot_token or config['bot_token'] or '').strip()
        chat = str(chat_id or config['chat_id'] or '').strip()
        if not token or not chat:
            _logger.info('Telegram: sin token/chat configurado, omito envío.')
            return False
        url = 'https://api.telegram.org/bot%s/sendMessage' % token
        ok = True
        for chunk in self._split_message(text):
            try:
                resp = requests.post(
                    url,
                    json={'chat_id': chat, 'text': chunk},
                    timeout=10,
                )
                if resp.status_code != 200:
                    _logger.warning('Telegram API error %s: %s', resp.status_code, resp.text[:500])
                    ok = False
            except Exception as e:  # noqa: BLE001 - no debe romper el form
                _logger.exception('Telegram: fallo de conexión: %s', e)
                return False
        return ok

    @api.model
    def build_form_message(self, model_label, record_values, custom='', meta=''):
        """Arma el texto de notificación a partir de los valores del form."""
        lines = ['🔔 Nuevo formulario: %s' % (model_label or 'Website')]
        safe_vals = dict(record_values or {})
        # ocultar firma interna
        safe_vals.pop('website_form_signature', None)
        # campos principales primero si existen
        for key in ('subject', 'name', 'partner_name', 'contact_name', 'email_from', 'email', 'phone', 'phone_number'):
            if safe_vals.get(key):
                lines.append('%s: %s' % (key, self.html_to_text(safe_vals.pop(key))[:500]))
        for key, val in safe_vals.items():
            if key.startswith('_') or key in ('context',):
                continue
            if isinstance(val, bytes):
                continue
            txt = self.html_to_text(val) if isinstance(val, str) and '<' in val else str(val or '')
            if len(txt) > 1000:
                txt = txt[:1000] + '…'
            lines.append('%s: %s' % (key, txt))
        if custom:
            lines.append('')
            lines.append('— Otros datos —')
            lines.append(self.html_to_text(custom)[:2000])
        body = '\n'.join(lines)
        # Telegram: cuerpo completo, cortado al límite real en send_message (split)
        return body[:15000]
