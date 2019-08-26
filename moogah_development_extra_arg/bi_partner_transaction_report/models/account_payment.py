# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
##################################################################################

from openerp import models, fields, api, _
from openerp.exceptions import ValidationError
from ast import literal_eval


class AccountPayment(models.Model):
    _inherit = "account.payment"

    unmatched_amount = fields.Monetary(
        compute='_compute_matched_amounts',
        currency_field='currency_id',
    )

    @api.multi
    @api.depends(
        'state',
        'payment_group_id',
        'amount',
        'payment_group_id.matched_move_line_ids.payment_group_matched_amount')
    def _compute_matched_amounts(self):
        for rec in self:
            if rec.state != 'posted':
                continue
            rec.unmatched_amount = 0.0
            if rec.payment_group_id:
                rec.matched_amount = rec.payment_group_matched_amount(rec.payment_group_id.matched_move_line_ids)
                rec.unmatched_amount = rec.amount - rec.matched_amount


    def payment_group_matched_amount(self, matched_move_line_ids):
        payment_move_lines = self.mapped('move_line_ids')
        payment_partial_lines = self.env[
            'account.partial.reconcile'].search([
            '|',
            ('credit_move_id', 'in', payment_move_lines.ids),
            ('debit_move_id', 'in', payment_move_lines.ids),
        ])
        payment_group_matched_amount = 0.0
        for matched_move_line_id in matched_move_line_ids:
            matched_amount = 0.0
            for pl in (matched_move_line_id.matched_debit_ids + matched_move_line_id.matched_credit_ids):
                if pl in payment_partial_lines:
                    matched_amount += pl.amount
            payment_group_matched_amount += matched_amount
        return payment_group_matched_amount
