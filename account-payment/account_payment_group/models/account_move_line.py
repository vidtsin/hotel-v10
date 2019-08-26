# -*- coding: utf-8 -*-
# © 2016 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import models, fields, api
# from openerp.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.tools.misc import formatLang
from odoo.tools import float_is_zero, float_compare
from odoo.tools.safe_eval import safe_eval
from lxml import etree

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.multi
    def action_open_related_invoice(self):
        self.ensure_one()
        record = self.invoice_id
        if not record:
            return False
        if record.type in ['in_refund', 'in_invoice']:
            view_id = self.env.ref('account.invoice_supplier_form').id
        else:
            view_id = self.env.ref('account.invoice_form').id
        return {
            'type': 'ir.actions.act_window',
            'res_model': record._name,
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': record.id,
            'view_id': view_id,
        }

    @api.multi
    def compute_payment_group_matched_amount(self):
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
            matched_amount = 0.0
            for pl in (rec.matched_debit_ids + rec.matched_credit_ids):
                if pl in payment_partial_lines:
                    matched_amount += pl.amount
            rec.payment_group_matched_amount = matched_amount

    payment_group_matched_amount = fields.Monetary(
        compute='compute_payment_group_matched_amount',
        currency_field='company_currency_id',
    )

    #std overwritten
    def _get_pair_to_reconcile(self):
        if self[0].company_id.arg_sortdate:
            # field is either 'amount_residual' or 'amount_residual_currency' (if the reconciled account has a secondary currency set)
            field = self[0].account_id.currency_id and 'amount_residual_currency' or 'amount_residual'
            rounding = self[0].company_id.currency_id.rounding
            if self[0].currency_id and all([x.amount_currency and x.currency_id == self[0].currency_id for x in self]):
                # or if all lines share the same currency
                field = 'amount_residual_currency'
                rounding = self[0].currency_id.rounding
            if self._context.get('skip_full_reconcile_check') == 'amount_currency_excluded':
                field = 'amount_residual'
            elif self._context.get('skip_full_reconcile_check') == 'amount_currency_only':
                field = 'amount_residual_currency'
            # target the pair of move in self that are the oldest
            sorted_moves = sorted(self, key=lambda a: a.date_maturity)  # OJG was a.date
            debit = credit = False
            for aml in sorted_moves:
                if credit and debit:
                    break
                if float_compare(aml[field], 0, precision_rounding=rounding) == 1 and not debit:
                    debit = aml
                elif float_compare(aml[field], 0, precision_rounding=rounding) == -1 and not credit:
                    credit = aml
            return debit, credit
        else:
            return super(AccountMoveLine, self)._get_pair_to_reconcile()
