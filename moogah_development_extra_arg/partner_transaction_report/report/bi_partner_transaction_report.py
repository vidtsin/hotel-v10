# -*- coding: utf-8 -*-

import time
from operator import itemgetter

from odoo import api, models, _
from odoo.exceptions import UserError


class ReportPartnerTransaction(models.AbstractModel):
    _name = 'report.partner_transaction_report.report_partner_transaction'

    def _formatted(self, value, digit):
        formatted = ('%.' + str(digit) + 'f') % value
        return formatted

    def _format(self, value, currency=False):
        if self.env.context.get('no_format'):
            return value
        currency_id = currency or self.env.user.company_id.currency_id
        if currency_id.is_zero(value):
            value = abs(value)
        # res = formatLang(self.env, value, currency_obj=currency_id)
        formatted = ('%.' + '2' + 'f') % value
        res = formatted
        if currency_id and currency_id.symbol:
            if currency_id.position == 'after':
                res = '%s %s' % (res, currency_id.symbol)
            elif currency_id and currency_id.position == 'before':
                res = '%s %s' % (currency_id.symbol, res)
        return res

    def get_lines(self, data):
        lines = {}
        for partner in self.env['res.partner'].browse(data['form']['partner_ids']):
            partner_type = data['form']['type']
            if partner_type == 'customer':
                invoice_type = ['out_invoice', 'out_refund']
            else:
                invoice_type = ['in_refund', 'in_invoice']
            customer_invoices = self._get_invoices(data, partner, invoice_type)
            payment_group = self._get_payment_group(data, partner, partner_type)
            if customer_invoices or payment_group:
                currency = self._get_moves_by_currency(data, partner, invoice_type, partner_type)
                lines.update({partner.id: {'title': partner.name,
                                        'currency': currency}})
        return lines

    def _get_moves_by_currency(self, data, partner, invoice_type, partner_type):
        currency_lines = []
        for currency in self.env['res.currency'].search([]):
            globle_dict_list = []
            lines = []
            total_currency = {}
            grand_total_debit = 0.0
            grand_total_credit = 0.0
            total_invoice = self._get_invoices(data, partner, invoice_type, 'initial').filtered(
                lambda x: x.currency_id == currency)
            for inv in total_invoice:
                if inv.type in ['out_refund', 'in_invoice']:
                    grand_total_credit += inv.amount_total
                else:
                    grand_total_debit += inv.amount_total

            total_payment_group = self._get_payment_group(data, partner, partner_type, 'initial')
            total_currency_payment_group = self.filter_currency_payment_group(total_payment_group, currency)
            for cpg in total_currency_payment_group:
                amount = 0.0
                payment_line_currency = cpg.payment_ids and cpg.payment_ids[0].currency_id or cpg.currency2_id
                amount = sum(cpg.payment_ids.mapped('amount'))

                if payment_line_currency.id != currency.id and cpg.manual_currency_rate:
                    if currency.id != self.env.user.company_id.currency_id.id:
                        amount = amount / cpg.manual_currency_rate
                    else:
                        amount = amount * cpg.manual_currency_rate
                if partner_type == 'customer':
                    grand_total_credit += amount
                else:
                    grand_total_debit += amount

            grand_total_balance = grand_total_debit - grand_total_credit

            initial_balance = {
                'debit': self._format(grand_total_debit, currency),
                'credit': self._format(grand_total_credit, currency),
                'balance': self._format(grand_total_balance, currency),
                'title': _("Initial Balance"),
                'line_type': 'total',
            }

            balance = grand_total_balance
            total_debit = grand_total_debit
            total_credit = grand_total_credit

            invoices = self._get_invoices(data, partner, invoice_type).filtered(lambda x: x.currency_id == currency)
            for inv in invoices:
                debit = credit = 0.0
                if inv.type == ['out_refund', 'in_invoice']:
                    credit = inv.amount_total
                else:
                    debit = inv.amount_total
                globle_dict_list.append({
                    'obj': inv,
                    'date': inv.date_invoice,
                    'line_type': 'invoice',
                    'doc_type': inv.journal_document_type_id.display_name,
                    'number': inv.display_name,
                    'reference': inv.name,
                    'debit': debit,
                    'credit': credit,
                    'currency_rate': inv.manual_currency_rate,
                    'amount_in_currency': credit if inv.type == ['out_refund', 'in_invoice'] else debit,
                })

            payment_group = self._get_payment_group(data, partner, partner_type)
            currency_payment_group = self.filter_currency_payment_group(payment_group, currency)
            for cpg in currency_payment_group:
                payment_line_currency = cpg.currency2_id
                payment_amount = 0.0
                for pay in cpg.payment_ids:
                    payment_amount += pay.amount or 0.0
                    payment_line_currency = pay.currency_id

                debit = credit = 0.0
                amount_in_currency = payment_amount
                amount = payment_amount
                if cpg.manual_currency_rate and payment_line_currency.id != currency.id:
                    if currency.id != self.env.user.company_id.currency_id.id:
                        amount = payment_amount / cpg.manual_currency_rate
                    else:
                        amount = payment_amount * cpg.manual_currency_rate

                if partner_type == 'customer':
                    credit = amount
                else:
                    debit = amount

                globle_dict_list.append({
                    'obj': cpg,
                    'line_type': 'payment',
                    'date': cpg.payment_date,
                    'doc_type': cpg.receiptbook_id.display_name,
                    'number': cpg.display_name,
                    'reference': cpg.name,
                    'debit': debit,
                    'credit': credit,
                    'currency_rate': cpg.manual_currency_rate,
                    'amount_in_currency': amount_in_currency,
                    'payment_currency': payment_line_currency,
                })
            sorted_globle_dict_list = sorted(globle_dict_list, key=itemgetter('date'))
            for dict in sorted_globle_dict_list:
                if dict.get('line_type') == 'payment':
                    total_credit += dict['credit']
                    total_debit += dict['debit']
                    balance += dict['debit'] - dict['credit']
                    values = {
                        'title': dict['number'],
                        'line_type': dict['line_type'],
                        'date': dict['date'],
                        'doc_type': dict['doc_type'],
                        'number': dict['number'],
                        'reference': dict['reference'],
                        'currency_rate': self._formatted(dict['currency_rate'], 6),
                        'amount_in_currency': self._format(dict['amount_in_currency'], dict['payment_currency']),
                        'debit': self._format(dict['debit'], currency),
                        'credit': self._format(dict['credit'], currency),
                        'balance': self._format(balance, currency)
                    }
                    lines.append(values)
                    if data['form']['level'] == 'detailed':
                        lines = self.get_account_payment_line(dict['obj'], lines, currency, partner_type)

                else:
                    total_credit += dict['credit']
                    total_debit += dict['debit']
                    balance += dict['debit'] - dict['credit']
                    lines.append({
                        'title': dict['number'],
                        'line_type': dict['line_type'],
                        'date': dict['date'],
                        'doc_type': dict['doc_type'],
                        'number': dict['number'],
                        'reference': dict['reference'],
                        'currency_rate': self._formatted(dict['currency_rate'], 6),
                        'amount_in_currency': self._format(dict['amount_in_currency'], currency),
                        'debit': self._format(dict['debit'], currency),
                        'credit': self._format(dict['credit'], currency),
                        'balance': self._format(balance, currency)
                    })
            if sorted_globle_dict_list:
                total_currency = {
                    'title': _("Total Currency: ") + currency.name,
                    'line_type': 'total',
                    'debit': self._format(total_debit, currency),
                    'credit': self._format(total_credit, currency),
                    'balance': self._format(balance, currency)
                }

            if lines:
                currency_lines.append({'currency': {'title': _('Currency: ') + currency.name,
                                                  'initial_balance': initial_balance,
                                                  'lines': lines,
                                                  'total': total_currency}
                                       })
        return currency_lines

    def get_account_payment_line(self, payment_group_line, lines, currency, partner_type):
        line_currency = currency
        payment_total_debit = 0.0
        payment_total_credit = 0.0
        payment_total_balance = 0.0
        for payment in payment_group_line.payment_ids:
            name = payment.display_name or ""
            if payment_group_line.unmatched_amount:
                name = _("Advance")
                debit = credit = 0.0
                currency_amount = amount = payment.unmatched_amount and payment.unmatched_amount or payment.amount
                if payment.currency_id.id != line_currency.id and payment_group_line.manual_currency_rate:
                    if line_currency.id != self.env.user.company_id.currency_id.id:
                        amount = amount / payment_group_line.manual_currency_rate
                    else:
                        amount = amount * payment_group_line.manual_currency_rate

                if partner_type == 'customer':
                    credit = amount
                else:
                    debit = amount

                balance = debit - credit

                payment_total_debit += debit
                payment_total_credit += credit
                payment_total_balance += balance

                invoice_number = payment.display_name
                lines.append({
                    'title': name,
                    'line_type': 'payment_line',
                    'date': payment.payment_date,
                    'doc_type': payment.receiptbook_id.display_name,
                    'number': invoice_number,
                    'reference': '',
                    'currency_rate': self._formatted(payment_group_line.manual_currency_rate, 6),
                    'amount_in_currency': self._format(currency_amount, payment.currency_id),
                    'debit': self._format(debit, line_currency),
                    'credit': self._format(credit, line_currency),
                    'balance': self._format(balance, line_currency),
                })
        payment_line_currency = payment_group_line.payment_ids and payment_group_line.payment_ids[0].currency_id \
                                or payment_group_line.currency2_id
        for aml in payment_group_line.matched_move_line_ids.filtered(lambda x: x.invoice_id):
            amount = aml.with_context(payment_group_id=payment_group_line.id).payment_group_matched_amount
            currency_amount = aml.with_context(payment_group_id=payment_group_line.id).payment_group_matched_amount
            debit = credit = 0.0
            if payment_line_currency.id != self.env.user.company_id.currency_id.id \
                    and line_currency.id != self.env.user.company_id.currency_id.id:
                amount = currency_amount = aml.with_context(
                    payment_group_id=payment_group_line.id).payment_group_matched_amount_currency
            if payment_line_currency.id != line_currency.id and payment_group_line.manual_currency_rate:
                if line_currency.id == self.env.user.company_id.currency_id.id:
                    currency_amount = currency_amount / payment_group_line.manual_currency_rate
                    amount = currency_amount * payment_group_line.manual_currency_rate
                else:
                    amount = credit / payment_group_line.manual_currency_rate
            if partner_type == 'customer':
                credit = amount
            else:
                debit = amount

            balance = debit - credit

            payment_total_debit += debit
            payment_total_credit += credit
            payment_total_balance += balance

            invoice_number = aml.invoice_id.display_name

            lines.append({
                'title': invoice_number,
                'line_type': 'payment_line',
                'date': aml.date,
                'doc_type': payment_group_line.receiptbook_id.display_name,
                'number': invoice_number,
                'reference': '',
                'currency_rate': self._formatted(payment_group_line.manual_currency_rate, 6),
                'amount_in_currency': self._format(currency_amount, payment_line_currency),
                'debit': self._format(debit, line_currency),
                'credit': self._format(credit, line_currency),
                'balance': self._format(balance, line_currency),
            })

        lines.append({
            'line_type': 'total',
            'title': "Total",
            'debit': self._format(payment_total_debit, line_currency),
            'credit': self._format(payment_total_credit, line_currency),
            'balance': self._format(payment_total_balance, line_currency),
        })
        return lines

    def get_currency_section(self, payment_group_line):
        if payment_group_line.matched_move_line_ids:
            filter_payment = payment_group_line.matched_move_line_ids.filtered(lambda i: i.invoice_id)
            if filter_payment:
                return filter_payment[0].invoice_id.currency_id
        else:
            if payment_group_line.unmatched_amount and payment_group_line.payment_ids:
                return payment_group_line.payment_ids[0].currency_id

    def _get_invoices(self, data, partner, invoice_type, case=False):
        domain = [('partner_id', '=', partner.id),
                  ('state', 'not in', ['draft', 'cancel']),
                  ('type', 'in', invoice_type)]
        if case == 'initial':
            domain += [('date_invoice', '<', data['form']['initial_date'])]
        else:
            domain += [('date_invoice', '>=', data['form']['initial_date']),
                       ('date_invoice', '<=', data['form']['end_date'])]
        # TODO: Ver si afecta el order a a hora de sumar el balance inicial
        return self.env['account.invoice'].search(domain, order='date_invoice')

    def _get_payment_group(self, data, partner, partner_type, case=False):
        domain = [('partner_id', '=', partner.id),
                  ('partner_type', '=', partner_type),
                  ('state', '!=', 'draft')]
        if case == 'initial':
            domain += [('payment_date', '<', data['form']['initial_date'])]
        else:
            domain += [('payment_date', '>=', data['form']['initial_date']),
                       ('payment_date', '<=', data['form']['end_date'])]
        # TODO: Ver si afecta el order a a hora de sumar el balance inicial
        return self.env['account.payment.group'].search(domain, order='payment_date')

    def filter_currency_payment_group(self, payment_group, currency):
        filter_payment_group = payment_group.filtered(
            lambda x: x.mapped('matched_move_line_ids').filtered(
                lambda i: i.invoice_id and i.invoice_id.currency_id.id == currency.id)
                      or (not x.matched_move_line_ids and x.unmatched_amount and x.mapped('payment_ids').filtered(
                lambda p: p.currency_id and p.currency_id.id == currency.id)))
        return filter_payment_group

    @api.multi
    def render_html(self, docids, data=None):
        self.model = self.env.context.get('active_model')
        docs = self.env[self.model].browse(self.env.context.get('active_ids', []))
        lines = self.get_lines(data)
        if not lines:
            raise UserError(_('There is no information for the selected filters.'))
        docargs = {
            'doc_ids': self.ids,
            'doc_model': self.model,
            'data': data['form'],
            'docs': docs,
            'time': time,
            'lines': lines,
        }
        return self.env['report'].render('partner_transaction_report.report_partner_transaction', docargs)
