# -*- coding: utf-8 -*-
from odoo import models, api, fields, _

class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    @api.model
    def _test_function(self):
        self.env.ref('account.action_account_payment_from_invoices').unlink()
