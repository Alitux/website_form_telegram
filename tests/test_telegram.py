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

    def test_get_tracking_own_cookies(self):
        svc = self.env['website_form_telegram.service']
        tracking = svc.get_tracking({
            'wft_utm_source': 'facebook',
            'wft_utm_medium': 'cpc',
            'wft_utm_campaign': 'promo-octubre',
            'wft_gclid': 'abc123',
            'other': 'ignored',
        })
        self.assertEqual(tracking, {
            'utm_source': 'facebook',
            'utm_medium': 'cpc',
            'utm_campaign': 'promo-octubre',
            'gclid': 'abc123',
        })

    def test_get_tracking_fallback_odoo_cookies(self):
        svc = self.env['website_form_telegram.service']
        tracking = svc.get_tracking({
            'odoo_utm_source': 'google',
            'odoo_utm_medium': 'cpc',
        })
        self.assertEqual(tracking['utm_source'], 'google')
        self.assertEqual(tracking['utm_medium'], 'cpc')

    def test_get_tracking_empty(self):
        svc = self.env['website_form_telegram.service']
        self.assertEqual(svc.get_tracking({}), {})
        # None intenta leer del request actual; fuera de request debe dar {}
        self.assertEqual(svc.get_tracking(None), {})

    def test_format_tracking_block(self):
        svc = self.env['website_form_telegram.service']
        block = svc.format_tracking_block({'utm_source': 'facebook', 'gclid': 'abc'})
        self.assertIn('— Origen (UTM) —', block)
        self.assertIn('utm_source: facebook', block)
        self.assertIn('gclid: abc', block)
        self.assertEqual(svc.format_tracking_block({}), '')
