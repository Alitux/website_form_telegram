# -*- coding: utf-8 -*-
{
    'name': 'Website Form to Telegram',
    'summary': 'Reenvía todos los formularios del website (contacto, etc.) a Telegram',
    'description': """
Toma todos los envíos del form builder del website (/website/form/<model>)
— que normalmente crean un mail.mail y lo envían por correo —
y los reenvía a un chat/grupo/canal de Telegram vía Bot API.

- Config global: bot token + chat_id en Ajustes.
- No bloquea el formulario si Telegram falla.
- Convierte el cuerpo HTML a texto plano y respeta el límite de 4096 caracteres.
    """,
    'author': 'Alitux',
    'website': 'https://alitux.com.ar',
    'category': 'Website/Website',
    'version': '18.0.1.1.0',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'website', 'utm'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
    ],
    'application': False,
    'installable': True,
}
