# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
##############################################################################
import urlparse
import md5

from odoo.addons.payment_payulatam_bi.controllers.main import PayuLatamController

from odoo import api, fields, models, _
from odoo.exceptions import except_orm, Warning, RedirectWarning


class PaymentAcquirerPayulatam(models.Model):
    _inherit = 'payment.acquirer'

    def _get_payu_urls(self, environment):
        """ PayuLatam URLs
        """
        if environment == 'prod':
            return {'payu_form_url': 'https://checkout.payulatam.com/ppp-web-gateway-payu'}
        else:
            return {'payu_form_url': 'https://sandbox.checkout.payulatam.com/ppp-web-gateway-payu'}

    @api.model
    def _get_providers(self):
        providers = super(PaymentAcquirerPayulatam, self)._get_providers()
        providers.append(['payulatam', 'PayuLatam'])
        return providers

    provider = fields.Selection(selection_add=[('payulatam', 'Payulatam')])
    payulatam_merchantId = fields.Char(string='Merchant ID', required_if_provider='payulatam')
    payulatam_accountId = fields.Char(string='Account ID', required_if_provider='payulatam')
    payulatam_apiKey = fields.Char(string='API Key', required_if_provider='payulatam')

    def _payulatam_generate_hashing(self, values):
        data = '~'.join([
            values['ApiKey'],
            values['merchantId'],
            values['referenceCode'],
            values['amount'],
            values['currency']])
        m = md5.new()
        m.update(data)
        return m.hexdigest()

    @api.multi
    def payulatam_form_generate_values(self, values):
        payulatam_tx_values = dict(values)
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        if self.environment == 'prod':
            test = 0
        else:
            test = 1
        temp_paylatam_tx_values = dict(
            ApiKey=self.payulatam_apiKey,
            merchantId=self.payulatam_merchantId,
            accountId=self.payulatam_accountId,
            referenceCode=values['reference'],
            description=values['reference'],
            amount=str(values['amount']),
            tax=0,
            currency=values['currency'] and values['currency'].name or '',
            currency_sel=['ARS', 'BRL', 'CLP', 'COP', 'MXN', 'PEN', 'USD'],
            taxReturnBase=0,
            buyerEmail=values['partner_email'],
            test=test,
            responseUrl='%s' % urlparse.urljoin(
                base_url, PayuLatamController._return_url),
            # confirmationUrl='%s' % urlparse.urljoin(base_url, PayuLatamController._confirm_url),
        )
        temp_paylatam_tx_values['signature'] = self._payulatam_generate_hashing(temp_paylatam_tx_values)
        payulatam_tx_values.update(temp_paylatam_tx_values)
        return payulatam_tx_values

    @api.multi
    def payulatam_get_form_action_url(self):
        self.ensure_one()
        return self._get_payu_urls(self.environment)['payu_form_url']

PaymentAcquirerPayulatam()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
