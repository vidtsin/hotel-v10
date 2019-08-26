# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountPartialReconcile(models.Model):
    _inherit = "account.partial.reconcile"

    def create_exchange_rate_entry(self, aml_to_fix, amount_diff, diff_in_currency, currency, move_date):
        pay_group = self.env['account.payment.group'].search(
            [('to_pay_move_line_ids', 'in', aml_to_fix.ids), ('state', '=', 'draft')])
        if not pay_group:
            payment = aml_to_fix.mapped('payment_id')
            pay_group = payment and payment.payment_group_id and payment.payment_group_id.filtered(
                lambda p: p.state == 'draft')

        line_to_reconcile, partial_rec = super(AccountPartialReconcile, self).create_exchange_rate_entry(aml_to_fix,
                                                                                                         amount_diff,
                                                                                                         diff_in_currency,
                                                                                                         currency,
                                                                                                         move_date)

        if pay_group:
            line_to_reconcile.mapped('move_id').write(
                {'document_type_id': pay_group[0].receiptbook_id.document_type_id.id,
                 'document_number': pay_group[0].id})
        return line_to_reconcile, partial_rec
