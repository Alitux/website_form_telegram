# -*- coding: utf-8 -*-
import logging

from odoo.addons.website.controllers.form import WebsiteForm

_logger = logging.getLogger(__name__)


class WebsiteFormTelegram(WebsiteForm):
    """Intercepta todos los envíos del form builder y los reenvía a Telegram.

    El form builder de Odoo 18 vive en website/controllers/form.py y su
    método insert_record() crea el registro (normalmente un mail.mail que
    luego se envía por correo). Aquí lo extendemos para:

    1. Inyectar el origen del anuncio (UTM/gclid/fbclid desde cookies) en
       ``custom`` ANTES de crear el registro, para que quede guardado en el
       mail (body_html) y disponible para cualquier modelo destino.
    2. Notificar a Telegram sin alterar el flujo original: si Telegram falla,
       el formulario sigue respondiendo éxito.
    """

    def _inject_tracking(self, request, custom):
        """Anexa el bloque '— Origen (UTM) —' a custom. Nunca lanza excepción."""
        try:
            service = request.env['website_form_telegram.service'].sudo()
            cookies = getattr(request, 'cookies', None) or {}
            tracking = service.get_tracking(cookies)
            block = service.format_tracking_block(tracking)
            if not block:
                return custom
            if custom:
                return '%s\n\n%s' % (custom, block)
            return block
        except Exception as e:  # noqa: BLE001 - jamás romper el envío del form
            _logger.debug('WebsiteFormTelegram: no se pudo inyectar UTM: %s', e)
            return custom

    def insert_record(self, request, model, values, custom, meta=None):
        # 1. UTM primero: queda persistido en el registro (mail incluido),
        #    haya o no Telegram configurado.
        custom = self._inject_tracking(request, custom)
        record_id = super().insert_record(request, model, values, custom, meta=meta)
        # 2. Telegram: el mensaje ya incluye custom (con UTM) en ambas ramas.
        try:
            Env = request.env
            service = Env['website_form_telegram.service'].sudo()
            config = service._get_config()
            if not config['enabled'] or not config['bot_token'] or not config['chat_id']:
                return record_id
            model_name = model.sudo().model
            model_label = model.sudo().name or model_name

            if model_name == 'mail.mail' and record_id:
                mail = Env['mail.mail'].sudo().browse(record_id)
                subject = mail.subject or 'Formulario web'
                body_text = service.html_to_text(mail.body_html or mail.body or '')
                header = '🔔 Nuevo formulario: %s\n📌 Asunto: %s' % (model_label, subject)
                if custom:
                    header += '\n\n— Datos del formulario —\n%s' % service.html_to_text(custom)[:2000]
                if body_text:
                    header += '\n\n— Cuerpo completo —\n%s' % body_text
                service.send_message(header)
            elif record_id:
                msg = service.build_form_message(model_label, values, custom=custom, meta=meta or '')
                service.send_message(msg)
        except Exception as e:  # noqa: BLE001 - jamás romper el envío del form
            _logger.exception('WebsiteFormTelegram: no se pudo notificar a Telegram: %s', e)
        return record_id
