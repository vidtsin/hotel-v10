# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
##############################################################################

from odoo import api, fields, models

class PaymentTransactionPayuLatam(models.Model):
    _inherit = 'payment.transaction'

    pos_order_id = fields.Many2one('pos.order', string='POS Order')

    @api.model
    def create_transaction_data(self, payulatam_id, reference, total, currency_id, partner_id):
        if payulatam_id and reference and total and currency_id and partner_id:
            self.create({'acquirer_id': payulatam_id,
                          'reference': self.get_next_reference(reference),
                          'amount': total,
                          'currency_id': currency_id,
                          'partner_id': partner_id})
        return True



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:        
