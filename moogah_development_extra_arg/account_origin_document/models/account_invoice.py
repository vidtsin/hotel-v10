# -*- coding: utf-8 -*-
###############################################################################
#
#   account_origin_document for Odoo
#   Copyright (C) 2004-today OpenERP SA (<http://www.openerp.com>)
#   Copyright (C) 2017-today Troova Software Development Group (troovacomercial@gmail.com).
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as
#   published by the Free Software Foundation, either version 3 of the
#   License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

import json
from odoo import api, exceptions, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare

class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    payments_widget = fields.Text(compute='_get_payment_info_JSON')
    copy_origin = fields.Char(string='Source Document', compute='_compute_copy_origin',
                         help="Reference of the document that produced this invoice.",
                         readonly=True, states={'draft': [('readonly', False)]})

    @api.one
    @api.depends('payment_move_line_ids.amount_residual')
    def _get_payment_info_JSON(self):
        self.payments_widget = json.dumps(False)
        if self.payment_move_line_ids:
            info = {'title': _('Less Payment'), 'outstanding': False, 'content': []}
            currency_id = self.currency_id
            for payment in self.payment_move_line_ids:
                payment_currency_id = False
                if self.type in ('out_invoice', 'in_refund'):
                    amount = sum(
                        [p.amount for p in payment.matched_debit_ids if p.debit_move_id in self.move_id.line_ids])
                    amount_currency = sum([p.amount_currency for p in payment.matched_debit_ids if
                                           p.debit_move_id in self.move_id.line_ids])
                    if payment.matched_debit_ids:
                        payment_currency_id = all([p.currency_id == payment.matched_debit_ids[0].currency_id for p in
                                                   payment.matched_debit_ids]) and payment.matched_debit_ids[
                                                  0].currency_id or False
                elif self.type in ('in_invoice', 'out_refund'):
                    amount = sum(
                        [p.amount for p in payment.matched_credit_ids if p.credit_move_id in self.move_id.line_ids])
                    amount_currency = sum([p.amount_currency for p in payment.matched_credit_ids if
                                           p.credit_move_id in self.move_id.line_ids])
                    if payment.matched_credit_ids:
                        payment_currency_id = all([p.currency_id == payment.matched_credit_ids[0].currency_id for p in
                                                   payment.matched_credit_ids]) and payment.matched_credit_ids[
                                                  0].currency_id or False
                # get the payment value in invoice currency
                if payment_currency_id and payment_currency_id == self.currency_id:
                    amount_to_show = amount_currency
                else:
                    amount_to_show = payment.company_id.currency_id.with_context(date=payment.date).compute(amount,
                                                                                                            self.currency_id)
                if float_is_zero(amount_to_show, precision_rounding=self.currency_id.rounding):
                    continue
                payment_ref = payment.move_id.name
                if payment.move_id.ref:
                    payment_ref += ' (' + payment.move_id.ref + ')'
                move_id = payment.move_id.id
                type = 'move'
                if payment.payment_id:
                    payment_ref = payment.payment_id.display_name
                    move_id = payment.payment_id.payment_group_id.id
                    type = 'payment'
                elif payment.invoice_id:
                    payment_ref = payment.invoice_id.display_name
                    move_id = payment.invoice_id.id
                    type = 'invoice'
                info['content'].append({
                    'name': payment.name,
                    'journal_name': payment.journal_id.name,
                    'amount': amount_to_show,
                    'currency': currency_id.symbol,
                    'digits': [69, currency_id.decimal_places],
                    'position': currency_id.position,
                    'date': payment.date,
                    'payment_id': payment.id,
                    'move_id': move_id,
                    'ref': payment_ref,
                    'type': type,
                })
            self.payments_widget = json.dumps(info)

    @api.multi
    def invoice_validate(self):
        result = super(AccountInvoice, self).invoice_validate()
        for inv in self:
            move = inv.move_id
            move_vals = {}
            if inv.type == 'out_invoice':
                move_vals['origin_document'] = inv.display_name
                move_vals['type_document'] = 'account_invoice_c'
                move_vals['document_id'] = inv.id
            elif inv.type == 'in_invoice':
                move_vals['origin_document'] = inv.display_name
                move_vals['type_document'] = 'account_invoice_v'
                move_vals['document_id'] = inv.id
            if inv.type == 'out_refund':
                move_vals['origin_document'] = inv.display_name
                move_vals['type_document'] = 'account_invoice_rc'
                move_vals['document_id'] = inv.id
            elif inv.type == 'in_refund':
                move_vals['origin_document'] = inv.display_name
                move_vals['type_document'] = 'account_invoice_rv'
                move_vals['document_id'] = inv.id
            move.write(move_vals)
        return result

    @api.multi
    def action_open_invoice(self):
        for rec in self:
            self.ensure_one()
            if rec.refund_invoice_id.type in ['out_invoice', 'in_invoice']:
                if rec.refund_invoice_id.type == 'out_invoice':
                    action = self.env.ref('account.action_invoice_tree2').read()[0]
                    form_view_id = self.env.ref('account.invoice_form').id
                elif rec.refund_invoice_id.type == 'in_invoice':
                    action = self.env.ref('account.action_invoice_tree1').read()[0]
                    form_view_id = self.env.ref('account.invoice_supplier_form').id

                action['views'] = [(form_view_id, 'form')]
                action['res_id'] = rec.refund_invoice_id.id
                action.pop('target', None)
                return action
        return True

    @api.model
    def _prepare_refund(self, invoice, date_invoice=None, date=None, description=None, journal_id=None):
        values = super(AccountInvoice, self)._prepare_refund(invoice, date_invoice, date, description, journal_id)
        values['origin'] = invoice.display_name
        return values

    # @api.model
    # def create(self, values):
    #     if not values.get('name'):
    #         values['name'] = 'bbbb'
    #     return super(AccountInvoice, self).create(values)

    @api.one
    def _compute_copy_origin(self):
        self.copy_origin = self.origin
