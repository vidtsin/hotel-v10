# -*- coding: utf-8 -*-

from odoo import fields, models, api


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    account_user_access = fields.Boolean(
        compute='_compute_account_user_access')

    @api.multi
    def _compute_account_user_access(self):
        users_obj = self.env['res.users']
        for invoice in self:
            invoice.account_user_access = (users_obj.has_group(
                'account.group_account_user') or users_obj.has_group(
                'account.group_account_manager'))
