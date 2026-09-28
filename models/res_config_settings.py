# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    telegram_enabled = fields.Boolean(
        string='Enviar formularios web a Telegram',
        config_parameter='website_form_telegram.enabled',
    )
    telegram_bot_token = fields.Char(
        string='Bot Token',
        config_parameter='website_form_telegram.bot_token',
    )
    telegram_chat_id = fields.Char(
        string='Chat ID',
        config_parameter='website_form_telegram.chat_id',
        help='ID del chat, grupo o canal. Ej: 123456789 o -1001234567890 para grupos/canal.',
    )

    def action_test_telegram(self):
        self.ensure_one()
        service = self.env['website_form_telegram.service']
        service.send_message(
            '🔔 Test OK: notificaciones de formularios web activas.',
            chat_id=self.telegram_chat_id,
            bot_token=self.telegram_bot_token,
        )
        return True
