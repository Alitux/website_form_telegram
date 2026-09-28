# -*- coding: utf-8 -*-
from unittest.mock import patch

from odoo.tests import TransactionCase


class TestTelegramService(TransactionCase):
    def test_html_to_text(self):
        svc = self.env['website_form_telegram.service']
        self.assertEqual(
            svc.html_to_text('<p>Hola<br/>Mundo</p>'),
            'Hola\nMundo',
        )

    def test_split_message(self):
        svc = self.env['website_form_telegram.service']
        long_text = 'a' * 5000
        chunks = svc._split_message(long_text)
        self.assertEqual(len(chunks), 2)
        self.assertTrue(all(len(c) <= 4096 for c in chunks))

    def test_build_form_message(self):
        svc = self.env['website_form_telegram.service']
        msg = svc.build_form_message('Contact', {'name': 'Juan', 'email': 'j@x.com'}, custom='tel : 123')
        self.assertIn('Juan', msg)
        self.assertIn('tel', msg)

    def test_send_message_no_config(self):
        svc = self.env['website_form_telegram.service']
        # sin token/chat -> False pero sin excepción
        self.assertFalse(svc.send_message('hola'))

    def test_send_message_ok(self):
        svc = self.env['website_form_telegram.service']
        self.env['ir.config_parameter'].sudo().set_param('website_form_telegram.bot_token', 'TOKEN')
        self.env['ir.config_parameter'].sudo().set_param('website_form_telegram.chat_id', '123')
        with patch('requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.text = 'ok'
            self.assertTrue(svc.send_message('hola'))
            mock_post.assert_called_once()
