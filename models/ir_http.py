# -*- coding: utf-8 -*-
import logging

from odoo import models
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

# Parámetros de tracking que persistimos en cookies propias.
# Odoo (módulo utm) solo guarda utm_campaign/source/medium; el resto
# (content, term, gclid, fbclid) no lo persiste nadie, por eso lo hacemos acá.
TRACKING_PARAMS = (
    'utm_source',
    'utm_medium',
    'utm_campaign',
    'utm_content',
    'utm_term',
    'gclid',
    'fbclid',
)

COOKIE_PREFIX = 'wft_'
COOKIE_MAX_AGE = 31 * 24 * 3600  # 31 días, igual que odoo_utm_*
COOKIE_MAX_LEN = 500


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _set_wft_tracking(cls, response):
        """Persiste los parámetros de tracking de la URL en cookies propias.

        Se ejecuta en cada respuesta (mismo mecanismo que usa el módulo utm
        en ir_http._set_utm) para que el origen del anuncio sobreviva a la
        navegación: el visitante llega con ?utm_... a la landing y días
        después envía el formulario con las cookies intactas.
        """
        response = Response.load(response)
        try:
            domain = request.httprequest.host
        except Exception:  # noqa: BLE001 - nunca romper el dispatch
            return
        params = request.params or {}
        cookies = request.cookies or {}
        for param in TRACKING_PARAMS:
            value = params.get(param)
            if not value or not isinstance(value, str):
                continue
            value = value.strip()[:COOKIE_MAX_LEN]
            if not value:
                continue
            cookie_name = COOKIE_PREFIX + param
            if cookies.get(cookie_name) == value:
                continue
            try:
                response.set_cookie(
                    cookie_name, value,
                    max_age=COOKIE_MAX_AGE, domain=domain, cookie_type='optional',
                )
            except Exception as e:  # noqa: BLE001 - no romper otras cookies
                _logger.debug('WFT tracking: no se pudo setear cookie %s: %s', cookie_name, e)

    @classmethod
    def _post_dispatch(cls, response):
        try:
            cls._set_wft_tracking(response)
        except Exception as e:  # noqa: BLE001 - jamás romper el dispatch
            _logger.debug('WFT tracking: fallo en _post_dispatch: %s', e)
        super()._post_dispatch(response)
