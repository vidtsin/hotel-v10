# -*- coding: utf-8 -*-                                                    
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.#
#################################################################################

from odoo import api, fields, models, _

class account_invoice(models.Model):
    _inherit = 'account.invoice'
    
    @api.multi
    def open_invoice_from_report(self):
        view_id = self.get_formview_id()
        return ['account.invoice', self.id, _('View Invoice'), view_id]
#         mod_obj = self.env['ir.model.data']
#         view_id = mod_obj.xmlid_to_res_id('account.invoice_form')
#         return {
#             'name': _('Customer Invoice'),
#             'view_type': 'form',
#             'context': {},
#             'view_mode': 'form',
#             'res_model': 'account.invoice',
#             'views': [(view_id, 'form')],
#             'type': 'ir.actions.act_window',
#             'target': 'current',
#             'res_id': self.id,
#             'view_id':view_id,
#             }
#         
