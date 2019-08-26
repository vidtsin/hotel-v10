# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
##############################################################################
import logging
import pprint
import werkzeug
import urlparse

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PayuLatamController(http.Controller):
    _cancel_url = '/payment/payulatam/cancel'
    _exception_url = '/payment/payulatam/error'
    _return_url = '/payment/payulatam/return'

    @http.route([_return_url, _cancel_url, _exception_url], type='http', auth='public')
    def payulatam_return(self, **post):
        """ Payu Latam."""
        _logger.info(
            'Payu: entering form_feedback with post data %s', pprint.pformat(post))
        if post:
            request.env['payment.transaction'].sudo().form_feedback(
                post, 'payulatam')
        base_url = request.env['ir.config_parameter'].get_param('web.base.url')
        return request.render('payment_payulatam_bi.payment_payulatam_redirect', {
            'return_url': '%s' % urlparse.urljoin(
                base_url, '/shop/payment/validate')
        })
