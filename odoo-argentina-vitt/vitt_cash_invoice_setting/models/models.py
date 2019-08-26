# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError,UserError

class AccountPaymentTerm(models.Model):
    _inherit = 'account.payment.term'

    cash = fields.Boolean(string="Cash",translate=True)
    cash_account_id = fields.Many2one('account.account',string="Cash Account",translate=True)

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.onchange('payment_term_id', 'date_invoice')
    def _onchange_payment_term_date_invoice(self):
        super(AccountInvoice, self)._onchange_payment_term_date_invoice()
        if self.type in ['out_invoice','out_refund']:
            if self.payment_term_id.cash:
                self.account_id = self.payment_term_id.cash_account_id.id
            else:
                self.account_id = self.partner_id.property_account_receivable_id.id

    @api.onchange('purchase_id')
    def purchase_order_change(self):
        res = super(AccountInvoice, self).purchase_order_change()
        self._onchange_partner_id()
        return res

class AccountInvoiceRefund(models.TransientModel):
    _inherit = "account.invoice.refund"

    def invoice_refund(self):
        res = super(AccountInvoiceRefund, self).invoice_refund()
        invoice_id = self.env['account.invoice'].browse(self._context.get('active_id', False))
        nc_id = res['domain'][1][2]
        nc = self.env['account.invoice'].search([('id','=',int(nc_id[0]))])
        nc.payment_term_id = invoice_id.payment_term_id.id
        return res
