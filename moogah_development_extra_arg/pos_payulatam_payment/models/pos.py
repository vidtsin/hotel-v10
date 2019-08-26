# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
##############################################################################

from odoo.http import request
from odoo import api, fields, models, _, tools
import logging
_logger = logging.getLogger(__name__)


class account_journal(models.Model):
    _inherit = 'account.journal'

    payulatam = fields.Boolean(string='POS PayuLatam Payment Acquirer')
    payulatam_config_id = fields.Many2one('payment.acquirer', string='Payment configuration', help='The configuration of PayuLatam used for this journal')

class PosOrder(models.Model):
    _inherit = 'pos.order'

    order_transcation_id = fields.Many2one('payment.transaction', string='Transaction Ref')
    @api.model
    def create_from_ui(self, orders):
        order_ids = super(PosOrder, self).create_from_ui(orders)
        for order_id in order_ids:
            try:
                pos_order = self.browse(order_id)
                if pos_order:
                    ref_order = [o['data'] for o in orders if o['data'].get('name') == pos_order.pos_reference]
                    transaction_rec = self.env['payment.transaction'].search([('reference', '=', pos_order.pos_reference)], limit=1)
                    if transaction_rec:
                        transaction_rec.pos_order_id = pos_order.id
                    for order in ref_order:
                        order.order_transcation_id = order.id
            except Exception as e:
                _logger.error('Error in payment transaction: %s', tools.ustr(e))
        return order_ids


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
