# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
##############################################################################
import logging

from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.tools.float_utils import float_compare
from odoo.tools.translate import _

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class PaymentTransactionPayuLatam(models.Model):
    _inherit = 'payment.transaction'

    payulatam_txnid = fields.Char(string='Transaction ID')
    payulatam_id = fields.Char(string="Reference Pol ID")
    psebank = fields.Char(string="PSEBank")
    cus = fields.Char(string="Cus")

    _payulatam_valid_tx_status = 4
    _payulatam_decline_tx_status = 6
    _payulatam_error_tx_status = 104
    _payulatam_expired_tx_status = 5
    _payulatam_pending_tx_status = 7

# --------------------------------------------------
# FORM RELATED METHODS
# --------------------------------------------------

    @api.model
    def _payulatam_form_get_tx_from_data(self, data):
        """ Given a data dict coming from payu, verify it and find the related
        transaction record. """
        reference = data.get('referenceCode')
        pay_id = data.get('transactionId')
        shasign = data.get('signature')
        product_ref = data.get('referenceCode')
        if not reference or not pay_id or not shasign:
            error_msg = _('Payu: received data with missing reference (%s) or pay_id (%s) or shashign (%s)') % (
                reference, pay_id, shasign)
            raise ValidationError(error_msg)

        tx = self.search([('reference', '=', reference)])
        pay_acc_obj = self.env['payment.acquirer'].search([])
        res_country_obj = self.env['res.country'].search([])
        res_curr_obj = self.env['res.currency'].search([])
        sal_order_obj = self.env['sale.order'].search([('name', '=', product_ref)])

        for sale_rec in sal_order_obj: sale_rec.id

        for pay_acc in pay_acc_obj:
            if pay_acc.provider == 'payulatam':
               acquire_var = pay_acc.id
        if not tx or len(tx) > 1:
            if not tx:
                status_code = int(data.get('polTransactionState', '0'))
                if status_code == self._payulatam_valid_tx_status:
                    state = 'done'
                    state_message = ((data.get('message') or '') + '\n' + (
                        data.get('lapResponseCode') or '')) or 'Done'
                elif status_code == self._payulatam_pending_tx_status:
                    state = 'pending'
                    state_message = ((data.get('message') or '') + '\n' + (
                        data.get('lapResponseCode') or '')) or 'Pending'
                elif status_code == self._payulatam_decline_tx_status:
                    state = 'cancel'
                    state_message = ((data.get('message') or '') + '\n' + (
                        data.get('lapResponseCode') or '')) or 'Decline'
                else:
                    state = 'error'
                    state_message = ((data.get('message') or '') + '\n' + (data.get('lapResponseCode') or '')) or _('payulatam: feedback error')

                pay_acq_rec = self.create({
                    'reference': product_ref,
                    'acquirer_id': acquire_var,
                    'amount': data.get('TX_VALUE'),
                    'partner_country_id': sale_rec.partner_id.country_id.id,
                    'currency_id': sale_rec.user_id.company_id.currency_id.id,
                    'payulatam_txnid': data.get('transactionId'),
                    'payulatam_id': data.get('reference_pol'),
                    'partner_reference': sale_rec.client_order_ref,
                    'partner_id': sale_rec.partner_id.id,
                    'partner_address': sale_rec.partner_id.street,
                    'partner_email': sale_rec.partner_id.email,
                    'partner_city': sale_rec.partner_id.city,
                    'partner_zip': sale_rec.partner_id.zip,
                    'state': state,
                    'psebank': data.get('psebank'),
                    'cus': data.get('cus'),
                    'state_message': state_message
                })
                tx = pay_acq_rec
            #verify shasign
          # data.update({'ApiKey': pay_acq_rec.acquirer_id.payulatam_apiKey,
          #              'amount': data.get('TX_VALUE')
          #             })
          # shasign_check = pay_acq_rec.acquirer_id._payulatam_generate_hashing(data)
          # print "__________", shasign_check

          # if shasign_check.upper() != shasign.upper():
          #     error_msg = _('PayuLatam: invalid shasign, received %s, computed %s, for data %s') % (
          #         shasign, shasign_check, data)
          #     raise ValidationError(error_msg)
        return tx

    @api.model
    def _payulatam_form_get_invalid_parameters(self,data):
        invalid_parameters = []
        if self.acquirer_reference and data.get('transactionId') != self.acquirer_reference:
            invalid_parameters.append(
                ('Transaction Id', data.get('transactionId'), self.acquirer_reference))
        #check what is buyed
        if float_compare(float(data.get('TX_VALUE', '0.0')), self.amount, 2) != 0:
            invalid_parameters.append(
                ('Amount', data.get('TX_VALUE'), '%.2f' % self.amount))
        return invalid_parameters
    
    @api.model
    def _payulatam_form_validate(self, data):
        if self.state == 'done':
            _logger.warning('Payulatam: trying to validate an already validated tx (ref %s)' % self.reference)
            return True
        status_code = int(data.get('polTransactionState', '0'))
        if status_code == self._payulatam_valid_tx_status:
            self.write({
                'state': 'done',
                'payulatam_txnid': data.get('transactionId'),
                'payulatam_id': data.get('reference_pol'),
                'state_message': ((data.get('message') or '') + '\n' + (
                    data.get('lapResponseCode') or '')) or 'Done'
                })
            return True
        elif status_code == self._payulatam_pending_tx_status:
            self.write({
                'state': 'pending',
                'payulatam_txnid': data.get('transactionId'),
                'payulatam_id': data.get('reference_pol'),
                'state_message': ((data.get('message') or '') + '\n' + (
                    data.get('lapResponseCode') or '')) or 'Pending'
            })
            return True
        elif status_code == self._payulatam_decline_tx_status:
                self.write({
                    'state': 'cancel',
                    'payulatam_txnid': data.get('transactionId'),
                    'payulatam_id': data.get('reference_pol'),
                    'state_message': ((data.get('message') or '') + '\n' + (
                        data.get('lapResponseCode') or '')) or 'Decline'
                })
        else:
            error = data.get('lapTransactionState')
            _logger.info(error)
            self.write({
                'state': 'error',
                'state_message': data.get('message') or _(
                    'payulatam: feedback error'),
                'payulatam_txnid': data.get('transactionId'),
                'payulatam_id': data.get('reference_pol')
            })
            return False
        

PaymentTransactionPayuLatam()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
