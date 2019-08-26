# -*- coding: utf-8 -*-                                                    
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.#
#################################################################################

from odoo import api, fields, models, _

class account_payment_group(models.Model):
    _inherit = 'account.payment.group'
    
    @api.multi
    def open_payment_group_from_report(self):
        mod_obj = self.env['ir.model.data']
        view_id = mod_obj.xmlid_to_res_id('account_payment_group.view_account_payment_group_form')
        return ['account.payment.group',self.id, _('View Payment'), view_id]
    
class account_payment(models.Model):
    _inherit = 'account.payment'
    
    @api.multi
    def open_payment_from_report(self):
        mod_obj = self.env['ir.model.data']
        view_id = mod_obj.xmlid_to_res_id('account.view_account_payment_form')
        return ['account.payment',self.id, _('View Payment'), view_id]
    
