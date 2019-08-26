# -*- coding: utf-8 -*-                                                    
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.#
#################################################################################

from odoo import api, fields, models, _

class res_partner(models.Model):
    _inherit = 'res.partner'
       
    @api.multi
    def generate_partner_transaction_report(self):
        self.ensure_one()
        ctx = self.env.context.copy()
        ctx.update({
            'url': '/account_reports/output_format/partner_transaction_report/1', 
            'addActiveId': True, 
            'model': 'partner.transaction.report', 
            'lang': self.lang,
            'date_filter':'this_month',
        })
        return {
                # 'id': 'action_account_report_partner_transaction1',
                'type': 'ir.actions.client',
                'tag': 'account_report_generic',
                'context': ctx,
                'name': _("Customer Ledger"),
                'options': {'partner_id': self.id},
            }
        
        
    @api.multi
    def generate_vendor_transaction_report(self):
        self.ensure_one()
        ctx = self.env.context.copy()
        ctx.update({
            'url': '/account_reports/output_format/vendor_transaction_report/1', 
            'addActiveId': True, 
            'model': 'vendor.transaction.report', 
            'lang': self.lang,
            'date_filter':'this_month',
        })
        return {
                # 'id': 'action_account_report_vendor_transaction1',
                'type': 'ir.actions.client',
                'tag': 'account_report_generic',
                'context': ctx,
                'name': _("Vendor Ledger"),
                'options': {'partner_id': self.id},
            }