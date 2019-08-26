# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import models, api, fields, _
from odoo.exceptions import ValidationError


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.onchange('purchase_id')
    def purchase_order_change(self):
        res = super(AccountInvoice, self).purchase_order_change()
        # if not self.purchase_id:
        #     return res
        analytic_tag_obj = self.env['account.analytic.tag']
        if self.partner_id:
            self.account_id = self.partner_id.property_account_payable_id.id
        if self.purchase_id.analytic_tag_ids:
            self.analytic_tag_ids = analytic_tag_obj._set_tags(tags=self.analytic_tag_ids, new_tags=self.purchase_id.analytic_tag_ids)
        return res
