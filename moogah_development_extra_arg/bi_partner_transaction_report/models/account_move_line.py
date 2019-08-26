# -*- coding: utf-8 -*-
# © 2016 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import models, fields, api

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.multi
    def compute_payment_group_matched_amount_currency(self):
        """
        """
        payment_group_id = self._context.get('payment_group_id')
        if not payment_group_id:
            return False
        payments = self.env['account.payment.group'].browse(
            payment_group_id).payment_ids
        payment_move_lines = payments.mapped('move_line_ids')
        payment_partial_lines = self.env[
            'account.partial.reconcile'].search([
                '|',
                ('credit_move_id', 'in', payment_move_lines.ids),
                ('debit_move_id', 'in', payment_move_lines.ids),
            ])
        for rec in self:
            matched_amount_currency = 0.0
            for pl in (rec.matched_debit_ids + rec.matched_credit_ids):
                if pl in payment_partial_lines:
                    matched_amount_currency += pl.amount_currency
            rec.payment_group_matched_amount_currency = matched_amount_currency

    payment_group_matched_amount_currency = fields.Monetary(
        compute='compute_payment_group_matched_amount_currency',
        currency_field='currency_id',
    )

