# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools.misc import formatLang
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import xlsxwriter
import StringIO
from odoo.tools import config


class PaymentJournalReport(models.AbstractModel):
    _name = "payment.journal.report"
    _description = "Payment Journal Report"

    def _format(self, value, currency=False):
        if self.env.context.get('no_format') and not self.env.context.get('xlsx_format'):
            return value
        currency_id = currency or self.env.user.company_id.currency_id
        if currency_id.is_zero(value):
            value = abs(value)
        res = formatLang(self.env, value, currency_obj=currency_id)
        return res

    @api.model
    def get_lines(self, context_id, line_id=None):
        if type(context_id) == int:
            context_id = self.env['payment.journal.context.report'].search([['id', '=', context_id]])
        new_context = dict(self.env.context)
        new_context.update({
            'date_from': context_id.date_from,
            'date_to': context_id.date_to,
            'context_id': context_id,
            'payment_no': context_id.payment_no,
            'journal_ids': context_id.journal_ids.ids,
            'partner_id': context_id.partner_id.id,
            'analytic_tag_id': context_id.analytic_tag_id.id,
            'reference': context_id.reference,
            'confirmed': context_id.confirmed,
            'posted': context_id.posted,
            'detail_level': context_id.detail_level,
            'company_id': context_id.company_id.id,
        })
        if new_context.get('xlsx_format'):
            if new_context.get('detail_level') == 'per_supplier':
                res = self.with_context(new_context)._xlsx_lines(line_id)
            else:
                res = self.with_context(new_context)._overview_xlsx_lines(line_id)
        else:
            res = self.with_context(new_context)._lines(line_id)
        return res

    @api.model
    def _xlsx_lines(self, line_id=None):
        context = self.env.context
        lang_code = self.env.lang or 'en_US'
        lang = self.env['res.lang']
        lang_id = lang._lang_get(lang_code)
        date_format = lang_id.date_format
        lines = []
        payment_quantity = 0
        total_payment_journal_amount = 0.0
        apg_obj = self.env['account.payment.group']
        partner_obj = self.env['res.partner']
        used_currency = self.env.user.company_id.currency_id
        if context.get('company_id'):
            used_currency = self.env['res.company'].browse(context.get('company_id')).currency_id
        suppliers = partner_obj.search([('supplier', '=', True)])
        if context.get('partner_id'):
            suppliers = partner_obj.browse(context.get('partner_id'))
        for supplier in suppliers:
            domain = self._get_domain(context, supplier.id)
            sorted_apg = apg_obj.search(domain)
            for payment_group in sorted_apg:
                first_line = False
                total_amount = 0.0
                payment_currency = payment_group.currency2_id and payment_group.currency2_id \
                                   or payment_group.currency_id
                move_lines = payment_group.matched_move_line_ids.filtered(lambda x: x.invoice_id)
                if payment_group.state == 'confirmed':
                    move_lines = payment_group.to_pay_move_line_ids.filtered(lambda x: x.invoice_id)
                journals = payment_group.payment_ids.mapped('journal_id')
                if context.get('journal_ids'):
                    journals = payment_group.payment_ids.filtered(
                        lambda x: x.journal_id.id in context.get('journal_ids')).mapped('journal_id')
                if len(journals.ids) == 1:
                    payment_amount = sum(payment_group.payment_ids.filtered(
                        lambda x: x.journal_id == journals).mapped('amount'))
                    currency_amount = payment_amount
                    if payment_group.payment_ids[0].currency_id != used_currency:
                        currency_amount = currency_amount * payment_group.manual_currency_rate
                    # currency_amount = payment_currency.compute(payment_amount, used_currency)
                    total_amount += currency_amount
                    for move_line in move_lines:
                        number = not first_line and payment_group.display_name or ''
                        payment_date = not first_line and datetime.strptime(payment_group.payment_date,
                                                                            DEFAULT_SERVER_DATE_FORMAT).strftime(
                            date_format) or None
                        supplier_name = not first_line and supplier.name or ''
                        lines.append({
                            'id': move_line.id,
                            'type': 'line_id',
                            'journal_id': not first_line and journals[0].id or False,
                            'total_journal': not first_line and currency_amount or 0.0,
                            'total_journal_in_currency': not first_line and payment_amount or 0.0,
                            'move_id': False,
                            'name': 'Line',
                            'colspan': 0,
                            'footnotes': {},
                            'columns': [supplier_name, number, payment_date,
                                        move_line.invoice_id.display_name,
                                        not first_line and
                                        self._format(payment_amount, payment_group.payment_ids[0].currency_id) or '',
                                        not first_line and
                                        self._format(total_amount, used_currency) or ''],
                            'level': 1,
                        })
                        first_line = True
                        if not move_lines:
                            payment_date = datetime.strptime(payment_group.payment_date,
                                                             DEFAULT_SERVER_DATE_FORMAT).strftime(
                                date_format)
                            lines.append({
                                'id': payment_group.id,
                                'type': 'line_id',
                                'journal_id': not first_line and journals[0].id or False,
                                'total_journal': not first_line and currency_amount or 0.0,
                                'total_journal_in_currency': not first_line and payment_amount or 0.0,
                                'move_id': False,
                                'name': 'Line',
                                'colspan': 0,
                                'footnotes': {},
                                'columns': [supplier.name, payment_group.display_name, payment_date,
                                            '', self._format(payment_amount, payment_group.payment_ids[0].currency_id),
                                            self._format(total_amount, used_currency)],
                                'level': 1,
                            })
                            first_line = True

                else:
                    journal_array = []
                    for journal in journals:
                        amount = sum(payment_group.payment_ids.filtered(
                            lambda x: x.journal_id == journal).mapped('amount'))
                        journal_currency = payment_group.payment_ids.filtered(
                            lambda x: x.journal_id == journal).mapped('currency_id')
                        journal_array.append({'journal_id': journal.id, 'amount': amount, 'code': journal.code,
                                              'journal_currency': journal_currency})

                    last_journal = False
                    payment_amount_journal = journal_array[0]['amount'] if journal_array else 0.0
                    journal_currency = journal_array[0]['journal_currency'] if journal_array else payment_currency
                    currency_total_payment = self._get_total_amount_xlsx_per_supplier(
                        journal_array) if journal_array else 0.0
                    # total_amount = payment_currency.compute(currency_total_payment, used_currency)
                    total_amount = currency_total_payment
                    if journal_currency != used_currency:
                        total_amount = currency_total_payment * payment_group.manual_currency_rate
                    i = 0
                    for move_line in move_lines:
                        number = not first_line and payment_group.display_name or ''
                        payment_date = not first_line and datetime.strptime(payment_group.payment_date,
                                                                            DEFAULT_SERVER_DATE_FORMAT).strftime(
                            date_format) or None
                        supplier_name = not first_line and supplier.name or ''
                        if not last_journal:
                            payment_amount_journal = journal_array[i]['amount'] if journal_array else 0.0
                            journal_currency = journal_array[i][
                                'journal_currency'] if journal_array else payment_currency
                            currency_amount_journal = payment_amount_journal
                            if journal_currency != used_currency:
                                currency_amount_journal = currency_amount_journal * payment_group.manual_currency_rate
                            # currency_amount_journal = payment_currency.compute(
                            #     payment_amount_journal, used_currency)
                        else:
                            i = len(journal_array) - 1

                        if journal_array:
                            journal_payment_amount_line = journal_array[i]['code'] + ' ' + \
                                                          self._format(payment_amount_journal, journal_currency)
                            no_payment = False
                        else:
                            journal_payment_amount_line = self._format(payment_amount_journal,
                                                                       payment_currency) + '*'
                            no_payment = True
                        lines.append({
                            'id': move_line.id,
                            'type': 'line_id',
                            'journal_id': journal_array[i][
                                'journal_id'] if journal_array and not last_journal else False,
                            'total_journal': currency_amount_journal if journal_array and not last_journal else 0.0,
                            'total_journal_in_currency': journal_array[i][
                                'amount'] if journal_array and not last_journal else 0.0,
                            'move_id': False,
                            'name': 'Line',
                            'colspan': 0,
                            'footnotes': {},
                            'columns': [supplier_name, number, payment_date,
                                        move_line.invoice_id.display_name,
                                        not last_journal and journal_payment_amount_line or '',
                                        not last_journal and self._format(total_amount, used_currency) or ''],
                            'level': 1,
                            'no_payment_line': no_payment,
                        })
                        first_line = True
                        if not last_journal and journal_array:
                            journal_array[i]['show'] = True
                        if i == len(journal_array) - 1 and journal_array:
                            last_journal = True
                        i += 1
                    for journal in filter(lambda x: not x.get('show'), journal_array):
                        number = not first_line and payment_group.display_name or ''
                        payment_date = not first_line and datetime.strptime(payment_group.payment_date,
                                                                            DEFAULT_SERVER_DATE_FORMAT).strftime(
                            date_format) or None
                        supplier_name = not first_line and supplier.name or ''
                        payment_amount_journal = journal['amount']
                        currency_amount_journal = payment_amount_journal
                        if journal['journal_currency'] != used_currency:
                            currency_amount_journal = currency_amount_journal * payment_group.manual_currency_rate
                        # currency_amount_journal = payment_currency.compute(payment_amount_journal, used_currency)
                        lines.append({
                            'id': journal['journal_id'],
                            'type': 'line_id',
                            'journal_id': journal['journal_id'],
                            'total_journal': currency_amount_journal,
                            'total_journal_in_currency': journal['amount'],
                            'move_id': False,
                            'colspan': 0,
                            'name': 'Line',
                            'footnotes': {},
                            'columns': [supplier_name, number, payment_date, '', journal['code'] + ' ' +
                                        self._format(payment_amount_journal, journal['journal_currency']),
                                        not first_line and self._format(total_amount, used_currency) or ''],
                            'level': 1,
                        })
                        if not move_lines:
                            first_line = True

                if first_line:
                    lines.append(self._get_line_space('per_supplier', 'xlsx'))

                total_payment_journal_amount += total_amount
                payment_quantity = first_line and payment_quantity + 1 or payment_quantity
        if total_payment_journal_amount:
            lines.append({
                'id': supplier.id,
                'type': 'line_id',
                'name': _('Total Payment'),
                'colspan': 0,
                'footnotes': {},
                'columns': [_('Total Payment'), '', None, '', '',
                            self._format(total_payment_journal_amount, used_currency)],
                'level': 1,
            })
            lines.append(self._get_line_space('per_supplier', 'xlsx'))

        if payment_quantity:
            lines.append({
                'id': 0,
                'type': 'line_id',
                'name': _('Total Payment Quantity'),
                'colspan': 0,
                'footnotes': {},
                'columns': [_('Total Payment Quantity'), '', None, '', '', str(payment_quantity)],
                'level': 1,
            })
        return lines

    @api.model
    def _overview_xlsx_lines(self, line_id=None):
        context = self.env.context
        lang_code = self.env.lang or 'en_US'
        lang = self.env['res.lang']
        lang_id = lang._lang_get(lang_code)
        date_format = lang_id.date_format
        used_currency = self.env.user.company_id.currency_id
        if context.get('company_id'):
            used_currency = self.env['res.company'].browse(context.get('company_id')).currency_id
        lines = []
        payment_quantity = 0
        first_line = False
        apg_obj = self.env['account.payment.group']
        domain = self._get_domain(context)
        sorted_apg = apg_obj.search(domain)
        total_payment_amount = 0.0
        for payment_group in sorted_apg:
            payment_currency = payment_group.currency2_id and payment_group.currency2_id \
                               or payment_group.currency_id
            first_line = False
            total_amount = 0.0
            move_lines = payment_group.matched_move_line_ids.filtered(lambda x: x.invoice_id)
            if payment_group.state == 'confirmed':
                move_lines = payment_group.to_pay_move_line_ids.filtered(lambda x: x.invoice_id)
            journals = payment_group.payment_ids.mapped('journal_id')
            if context.get('journal_ids'):
                journals = payment_group.payment_ids.filtered(
                    lambda x: x.journal_id.id in context.get('journal_ids')).mapped('journal_id')
            if len(journals.ids) == 1:
                payment_amount = sum(payment_group.payment_ids.filtered(
                    lambda x: x.journal_id == journals).mapped('amount'))
                currency_amount = payment_amount
                if payment_group.payment_ids[0].currency_id != used_currency:
                    currency_amount = currency_amount * payment_group.manual_currency_rate
                # currency_amount = payment_currency.compute(payment_amount, used_currency)
                total_amount += currency_amount
                for move_line in move_lines:
                    supplier_name = not first_line and payment_group.partner_id.name or ''
                    number = not first_line and payment_group.display_name or ''
                    payment_date = not first_line and datetime.strptime(payment_group.payment_date,
                                                                        DEFAULT_SERVER_DATE_FORMAT).strftime(
                        date_format) or None
                    lines.append({
                        'id': move_line.id,
                        'type': 'line_id',
                        'journal_id': not first_line and journals[0].id or False,
                        'total_journal': not first_line and currency_amount or 0.0,
                        'total_journal_in_currency': not first_line and payment_amount or 0.0,
                        'move_id': move_line.move_id.id or False,
                        'colspan': 0,
                        'name': not first_line and _('Payment Journal') or '',
                        'footnotes': self.env.context['context_id']._get_footnotes('move_line_id', move_line.id),
                        'columns': [number, payment_date, supplier_name,
                                    move_line.invoice_id.display_name,
                                    not first_line and
                                    self._format(payment_amount, payment_group.payment_ids[0].currency_id) or ''],
                        'level': 1,
                    })
                    first_line = True

                if not move_lines:
                    payment_date = datetime.strptime(payment_group.payment_date,
                                                     DEFAULT_SERVER_DATE_FORMAT).strftime(
                        date_format)
                    lines.append({
                        'id': payment_group.id,
                        'type': 'line_id',
                        'journal_id': journals[0].id,
                        'total_journal': currency_amount,
                        'total_journal_in_currency': payment_amount,
                        'move_id': False,
                        'name': '',
                        'colspan': 0,
                        'footnotes': {},
                        'columns': [payment_group.display_name, payment_date, payment_group.partner_id.name,
                                    '', self._format(payment_amount, payment_group.payment_ids[0].currency_id)],
                        'level': 1,
                    })
                    first_line = True

                if first_line:
                    lines.append({
                        'id': payment_group.id,
                        'type': 'line_id',
                        'name': 'Total',
                        'colspan': 0,
                        'style': "border-style: none;",
                        'footnotes': self.env.context['context_id']._get_footnotes(
                            'o_account_reports_domain_total',
                            payment_group.id),
                        'columns': ['', None, '', '',
                                    self._format(total_amount, used_currency)],
                        'level': 1,
                    })
            else:
                journal_array = []
                for journal in journals:
                    amount = sum(payment_group.payment_ids.filtered(
                        lambda x: x.journal_id == journal).mapped('amount'))
                    journal_currency = payment_group.payment_ids.filtered(
                                lambda x: x.journal_id == journal).mapped('currency_id')
                    journal_array.append({'journal_id': journal.id, 'amount': amount, 'code': journal.code,
                                          'journal_currency': journal_currency})

                last_journal = False
                payment_amount_journal = journal_array[0]['amount'] if journal_array else 0.0
                i = 0
                for move_line in move_lines:
                    supplier_name = not first_line and payment_group.partner_id.name or ''
                    number = not first_line and payment_group.display_name or ''
                    payment_date = not first_line and datetime.strptime(payment_group.payment_date,
                                                                        DEFAULT_SERVER_DATE_FORMAT).strftime(
                        date_format) or None
                    if not last_journal:
                        payment_amount_journal = journal_array[i]['amount'] if journal_array else 0.0
                        journal_currency = journal_array[i]['journal_currency'] if journal_array else payment_currency
                        # currency_amount_journal = payment_currency.compute(
                        #     payment_amount_journal, used_currency)
                        currency_amount_journal = payment_amount_journal
                        if journal_currency != used_currency:
                            currency_amount_journal = currency_amount_journal * payment_group.manual_currency_rate
                        total_amount += currency_amount_journal
                    else:
                        i = len(journal_array) - 1

                    if journal_array:
                        journal_payment_amount_line = journal_array[i]['code'] + ' ' + \
                                                      self._format(payment_amount_journal, journal_currency)
                        no_payment = False
                    else:
                        journal_payment_amount_line = self._format(payment_amount_journal,
                                                                   payment_currency) + '*'
                        no_payment = True

                    lines.append({
                        'id': move_line.id,
                        'type': 'line_id',
                        'journal_id': journal_array[i]['journal_id'] if journal_array and not last_journal else False,
                        'total_journal': currency_amount_journal if journal_array and not last_journal else 0.0,
                        'total_journal_in_currency': journal_array[i][
                            'amount'] if journal_array and not last_journal else 0.0,
                        'move_id': move_line.move_id.id or False,
                        'colspan': 0,
                        'name': not first_line and _('Payment Journal') or '',
                        'footnotes': self.env.context['context_id']._get_footnotes('move_line_id', move_line.id),
                        'columns': [number, payment_date, supplier_name, move_line.invoice_id.display_name,
                                    not last_journal and journal_payment_amount_line or ''],
                        'level': 1,
                        'no_payment_line': no_payment,
                    })
                    first_line = True
                    if not last_journal and journal_array:
                        journal_array[i]['show'] = True
                    if i == len(journal_array) - 1 and journal_array:
                        last_journal = True
                    i += 1
                for journal in filter(lambda x: not x.get('show'), journal_array):
                    supplier_name = not first_line and payment_group.partner_id.name or ''
                    number = not first_line and payment_group.display_name or ''
                    payment_date = not first_line and datetime.strptime(payment_group.payment_date,
                                                                        DEFAULT_SERVER_DATE_FORMAT).strftime(
                        date_format) or None
                    payment_amount_journal = journal['amount']
                    currency_amount_journal = payment_amount_journal
                    if journal['journal_currency'] != used_currency:
                        currency_amount_journal = currency_amount_journal * payment_group.manual_currency_rate
                    # currency_amount_journal = payment_currency.compute(payment_amount_journal, used_currency)
                    total_amount += currency_amount_journal
                    lines.append({
                        'id': journal['journal_id'],
                        'type': 'line_id',
                        'journal_id': journal['journal_id'],
                        'total_journal': currency_amount_journal,
                        'total_journal_in_currency': journal['amount'],
                        'move_id': False,
                        'colspan': 0,
                        'name': '',
                        'footnotes': {},
                        'columns': [number, payment_date, supplier_name, '',
                                    journal['code'] + ' ' + self._format(
                                        payment_amount_journal, journal['journal_currency'])],
                        'level': 1,
                    })
                    if not move_lines:
                        first_line = True
                if first_line:
                    lines.append({
                        'id': payment_group.id,
                        'type': 'line_id',
                        'name': 'Total',
                        'colspan': 0,
                        'style': "border-style: none;",
                        'footnotes': self.env.context['context_id']._get_footnotes(
                            'o_account_reports_domain_total',
                            payment_group.id),
                        'columns': ['', None, '', '',
                                    self._format(total_amount, used_currency)],
                        'level': 1,
                    })
            total_payment_amount += total_amount
            payment_quantity = first_line and payment_quantity + 1 or payment_quantity
            if first_line:
                lines.append(self._get_line_space('overview', 'xlsx'))

        if first_line:
            lines.append({
                'id': 0,
                'type': 'line_id',
                'name': _('Total Payment'),
                'colspan': 0,
                'footnotes': {},
                'columns': [_('Total Payment'), None, '', '',
                            self._format(total_payment_amount, used_currency)],
                'level': 1,
            })
            lines.append(self._get_line_space('overview', 'xlsx'))
        if payment_quantity:
            lines.append({
                'id': 0,
                'type': 'line_id',
                'name': _('Total Payment Quantity'),
                'colspan': 0,
                'footnotes': {},
                'columns': [_('Total Payment Quantity'), None, '', '', str(payment_quantity)],
                'level': 1,
            })

        return lines

    @api.model
    def _lines(self, line_id=None):
        context = self.env.context
        lang_code = self.env.lang or 'en_US'
        lang = self.env['res.lang']
        lang_id = lang._lang_get(lang_code)
        date_format = lang_id.date_format
        used_currency = self.env.user.company_id.currency_id
        if context.get('company_id'):
            used_currency = self.env['res.company'].browse(context.get('company_id')).currency_id
        lines = []
        payment_quantity = 0
        total_payment_amount = 0.0
        first_line = False
        apg_obj = self.env['account.payment.group']
        partner_obj = self.env['res.partner']
        if context.get('detail_level') == 'per_supplier':
            suppliers = partner_obj.search([('supplier', '=', True)])
            if context.get('partner_id'):
                suppliers = partner_obj.browse(context.get('partner_id'))
            for supplier in suppliers:
                total_supplier_amount = 0.0
                domain = self._get_domain(context, supplier.id)
                sorted_apg = apg_obj.search(domain)
                partner_lines = [{
                    'id': supplier.id,
                    'partner_id': supplier.id,
                    'type': 'line',
                    'name': supplier.name,
                    'footnotes': {},
                    'columns': [supplier.name, '', '', '', ''],
                    'level': 1,
                    'unfoldable': False,
                    'unfolded': False,
                }]
                for payment_group in sorted_apg:
                    first_line = False
                    total_amount = 0.0
                    payment_currency = payment_group.currency2_id and payment_group.currency2_id \
                                       or payment_group.currency_id
                    move_lines = payment_group.matched_move_line_ids.filtered(lambda x: x.invoice_id)
                    if payment_group.state == 'confirmed':
                        move_lines = payment_group.to_pay_move_line_ids.filtered(lambda x: x.invoice_id)
                    journals = payment_group.payment_ids.mapped('journal_id')
                    if context.get('journal_ids'):
                        journals = payment_group.payment_ids.filtered(
                            lambda x: x.journal_id.id in context.get('journal_ids')).mapped('journal_id')
                    if len(journals.ids) == 1:
                        payment_amount = sum(payment_group.payment_ids.filtered(
                            lambda x: x.journal_id == journals).mapped('amount'))
                        currency_amount = payment_amount
                        if payment_group.payment_ids[0].currency_id != used_currency:
                            currency_amount = currency_amount * payment_group.manual_currency_rate
                        # currency_amount = payment_group.payment_ids[0].currency_id.compute(payment_amount, used_currency)
                        total_amount += currency_amount
                        for move_line in move_lines:
                            if not filter(lambda x: x.get('partner_id') and x.get('partner_id') == supplier.id, lines):
                                lines.extend(partner_lines)
                            number = not first_line and payment_group.display_name or ''
                            payment_date = not first_line and datetime.strptime(payment_group.payment_date,
                                                                                DEFAULT_SERVER_DATE_FORMAT).strftime(
                                date_format) or None
                            lines.append({
                                'id': move_line.id,
                                'type': 'line_id',
                                'journal_id': not first_line and journals[0].id or False,
                                'total_journal': not first_line and currency_amount or 0.0,
                                'total_journal_in_currency': not first_line and payment_amount or 0.0,
                                'move_id': move_line.move_id.id or False,
                                'name': '',
                                'footnotes': self.env.context['context_id']._get_footnotes('move_line_id',
                                                                                           move_line.id),
                                'columns': ['', number, payment_date,
                                            move_line.invoice_id.display_name,
                                            not first_line and
                                            self._format(payment_amount, payment_group.payment_ids[0].currency_id) or ''],
                                'level': 2,
                            })
                            first_line = True

                        if not move_lines:
                            if not filter(lambda x: x.get('partner_id') and x.get('partner_id') == supplier.id, lines):
                                lines.extend(partner_lines)
                            payment_date = datetime.strptime(payment_group.payment_date,
                                                             DEFAULT_SERVER_DATE_FORMAT).strftime(
                                date_format)
                            lines.append({
                                'id': payment_group.id,
                                'type': 'line_id',
                                'journal_id': journals[0].id,
                                'total_journal': currency_amount,
                                'total_journal_in_currency': payment_amount,
                                'move_id': False,
                                'name': '',
                                'footnotes': {},
                                'columns': ['', payment_group.display_name, payment_date,
                                            '', self._format(payment_amount, payment_group.payment_ids[0].currency_id)],
                                'level': 2,
                            })
                            first_line = True

                        if first_line:
                            lines.append({
                                'id': payment_group.id,
                                'type': 'total',
                                'name': _('Total'),
                                'style': "border-style: none;",
                                'footnotes': self.env.context['context_id']._get_footnotes('line_id',
                                                                                           payment_group.id),
                                'columns': ['', '', None, '', (self._format(total_amount, used_currency),
                                                               "", "border-top:1px solid;")],
                                'level': 1,
                            })
                    else:
                        journal_array = []
                        for journal in journals:
                            journal_currency = payment_group.payment_ids.filtered(
                                lambda x: x.journal_id == journal).mapped('currency_id')
                            amount = sum(payment_group.payment_ids.filtered(
                                lambda x: x.journal_id == journal).mapped('amount'))
                            journal_array.append({'journal_id': journal.id, 'amount': amount, 'code': journal.code,
                                                  'journal_currency': journal_currency})

                        last_journal = False
                        payment_amount_journal = journal_array[0]['amount'] if journals else 0.0
                        i = 0
                        for move_line in move_lines:
                            if not filter(lambda x: x.get('partner_id') and x.get('partner_id') == supplier.id, lines):
                                lines.extend(partner_lines)
                            number = not first_line and payment_group.display_name or ''
                            payment_date = not first_line and datetime.strptime(payment_group.payment_date,
                                                                                DEFAULT_SERVER_DATE_FORMAT).strftime(
                                date_format) or None
                            if not last_journal:
                                payment_amount_journal = journal_array[i]['amount'] if journal_array else 0.0
                                journal_currency = journal_array[i]['journal_currency'] if journal_array else payment_currency
                                currency_amount_journal = payment_amount_journal
                                if journal_currency != used_currency:
                                    currency_amount_journal = currency_amount_journal * payment_group.manual_currency_rate
                                # currency_amount_journal = journal_currency.compute(
                                #     payment_amount_journal, used_currency)
                                total_amount += currency_amount_journal
                            else:
                                i = len(journal_array) - 1

                            if journal_array:
                                journal_payment_amount_line = journal_array[i]['code'] + ' ' + \
                                                              self._format(payment_amount_journal, journal_currency)
                                no_payment = False
                            else:
                                journal_payment_amount_line = self._format(payment_amount_journal,
                                                                           payment_currency) + '*'
                                no_payment = True
                            lines.append({
                                'id': move_line.id,
                                'type': 'line_id',
                                'journal_id': journal_array[i][
                                    'journal_id'] if journal_array and not last_journal else False,
                                'total_journal': currency_amount_journal if journal_array and not last_journal else 0.0,
                                'total_journal_in_currency': journal_array[i][
                                    'amount'] if journal_array and not last_journal else 0.0,
                                'move_id': move_line.move_id.id or False,
                                'name': '',
                                'footnotes': self.env.context['context_id']._get_footnotes('move_line_id',
                                                                                           move_line.id),
                                'columns': ['', number, payment_date,
                                            move_line.invoice_id.display_name,
                                            not last_journal and journal_payment_amount_line or ''],
                                'level': 2,
                                'no_payment_line': no_payment
                            })
                            first_line = True
                            if not last_journal and journal_array:
                                journal_array[i]['show'] = True
                            if i == len(journal_array) - 1 and journal_array:
                                last_journal = True
                            i += 1
                        for journal in filter(lambda x: not x.get('show'), journal_array):
                            if not filter(lambda x: x.get('partner_id') and x.get('partner_id') == supplier.id, lines):
                                lines.extend(partner_lines)
                            number = not first_line and payment_group.display_name or ''
                            payment_date = not first_line and datetime.strptime(payment_group.payment_date,
                                                                                DEFAULT_SERVER_DATE_FORMAT).strftime(
                                date_format) or None
                            payment_amount_journal = journal['amount']
                            currency_amount_journal = payment_amount_journal
                            if journal['journal_currency'] != used_currency:
                                currency_amount_journal = currency_amount_journal * payment_group.manual_currency_rate
                            # currency_amount_journal = journal['journal_currency'].compute(payment_amount_journal, used_currency)
                            total_amount += currency_amount_journal
                            lines.append({
                                'id': journal['journal_id'],
                                'type': 'line_id',
                                'journal_id': journal['journal_id'],
                                'total_journal': currency_amount_journal,
                                'total_journal_in_currency': journal['amount'],
                                'move_id': False,
                                'colspan': 0,
                                'name': '',
                                'footnotes': {},
                                'columns': ['', number, payment_date, '', journal['code'] + ' ' +
                                            self._format(payment_amount_journal, journal['journal_currency'])],
                                'level': 2,
                            })
                            if not move_lines:
                                first_line = True

                        if first_line:
                            lines.append({
                                'id': payment_group.id,
                                'type': 'total',
                                'name': _('Total '),
                                'style': "border-style: none;",
                                'footnotes': self.env.context['context_id']._get_footnotes('line_id',
                                                                                           payment_group.id),
                                'columns': ['', '', None, '', (self._format(total_amount, used_currency),
                                                               "", "border-top:1px solid;")],
                                'level': 1,
                            })
                    total_supplier_amount += total_amount
                    payment_quantity = first_line and payment_quantity + 1 or payment_quantity
                total_payment_amount += total_supplier_amount
                if first_line and sorted_apg:
                    lines.append({
                        'id': supplier.id,
                        'type': 'o_account_reports_domain_total',
                        'name': _('Total per Supplier’s Payments'),
                        'footnotes': {},
                        'columns': [_('Total per Supplier’s Payments'), '', None, '',
                                    (self._format(total_supplier_amount, used_currency),
                                     "", "border-top:1px solid;")],
                        'level': 1,
                    })
                    lines.append(self._get_line_space('per_supplier'))

        else:
            domain = self._get_domain(context)
            sorted_apg = apg_obj.search(domain)
            for payment_group in sorted_apg:
                payment_currency = payment_group.currency2_id and payment_group.currency2_id \
                                   or payment_group.currency_id
                first_line = False
                total_amount = 0.0
                move_lines = payment_group.matched_move_line_ids.filtered(lambda x: x.invoice_id)
                if payment_group.state == 'confirmed':
                    move_lines = payment_group.to_pay_move_line_ids.filtered(lambda x: x.invoice_id)
                journals = payment_group.payment_ids.mapped('journal_id')
                if context.get('journal_ids'):
                    journals = payment_group.payment_ids.filtered(
                        lambda x: x.journal_id.id in context.get('journal_ids')).mapped('journal_id')
                if len(journals.ids) == 1:
                    payment_amount = sum(payment_group.payment_ids.filtered(
                        lambda x: x.journal_id == journals).mapped('amount'))
                    currency_amount = payment_amount
                    # currency_amount = payment_group.payment_ids[0].currency_id.compute(payment_amount, used_currency)
                    if payment_group.payment_ids[0].currency_id != used_currency:
                        currency_amount = currency_amount * payment_group.manual_currency_rate
                    total_amount += currency_amount
                    for move_line in move_lines:
                        supplier_name = not first_line and payment_group.partner_id.name or ''
                        number = not first_line and payment_group.display_name or ''
                        payment_date = not first_line and datetime.strptime(payment_group.payment_date,
                                                                            DEFAULT_SERVER_DATE_FORMAT).strftime(
                            date_format) or None
                        lines.append({
                            'id': move_line.id,
                            'type': 'line_id',
                            'journal_id': not first_line and journals[0].id or False,
                            'total_journal': not first_line and currency_amount or 0.0,
                            'total_journal_in_currency': not first_line and payment_amount or 0.0,
                            'move_id': move_line.move_id.id or False,
                            'colspan': 0,
                            'name': not first_line and _('Payment Journal') or '',
                            'footnotes': self.env.context['context_id']._get_footnotes('move_line_id', move_line.id),
                            'columns': [number, payment_date, supplier_name,
                                        move_line.invoice_id.display_name,
                                        not first_line and
                                        self._format(payment_amount, payment_group.payment_ids[0].currency_id) or ''],
                            'level': 1,
                        })
                        first_line = True

                    if not move_lines:
                        payment_date = datetime.strptime(payment_group.payment_date,
                                                         DEFAULT_SERVER_DATE_FORMAT).strftime(
                            date_format)
                        lines.append({
                            'id': payment_group.id,
                            'type': 'line_id',
                            'journal_id': journals[0].id,
                            'total_journal': currency_amount,
                            'total_journal_in_currency': payment_amount,
                            'move_id': False,
                            'name': '',
                            'footnotes': {},
                            'columns': [payment_group.display_name, payment_date, payment_group.partner_id.name,
                                        '', self._format(payment_amount, payment_group.payment_ids[0].currency_id)],
                            'level': 1,
                        })
                        first_line = True

                    if first_line:
                        lines.append({
                            'id': payment_group.id,
                            'type': 'total',
                            'name': '',
                            'colspan': 0,
                            'style': "border-style: none;",
                            'footnotes': self.env.context['context_id']._get_footnotes(
                                'o_account_reports_domain_total',
                                payment_group.id),
                            'columns': ['', None, '', '',
                                        (self._format(total_amount, used_currency), "", "border-top:1px solid;")],
                            'level': 1,
                        })
                else:
                    journal_array = []
                    for journal in journals:
                        journal_currency = payment_group.payment_ids.filtered(
                            lambda x: x.journal_id == journal).mapped('currency_id')
                        amount = sum(payment_group.payment_ids.filtered(
                            lambda x: x.journal_id == journal).mapped('amount'))
                        journal_array.append({'journal_id': journal.id, 'amount': amount, 'code': journal.code,
                                              'journal_currency': journal_currency})

                    last_journal = False
                    payment_amount_journal = journal_array[0]['amount'] if journals else 0.0
                    i = 0
                    for move_line in move_lines:
                        supplier_name = not first_line and payment_group.partner_id.name or ''
                        number = not first_line and payment_group.display_name or ''
                        payment_date = not first_line and datetime.strptime(payment_group.payment_date,
                                                                            DEFAULT_SERVER_DATE_FORMAT).strftime(
                            date_format) or None
                        if not last_journal:
                            payment_amount_journal = journal_array[i]['amount'] if journal_array else 0.0
                            journal_currency = journal_array[i][
                                'journal_currency'] if journal_array else payment_currency
                            # currency_amount_journal = journal_currency.compute(payment_amount_journal,
                            #                                                               used_currency)
                            currency_amount_journal = payment_amount_journal
                            if journal_currency != used_currency:
                                currency_amount_journal = currency_amount_journal * payment_group.manual_currency_rate
                            total_amount += currency_amount_journal
                        else:
                            i = len(journal_array) - 1

                        if journal_array:
                            journal_payment_amount_line = journal_array[i]['code'] + ' ' + \
                                                          self._format(payment_amount_journal, journal_currency)
                            no_payment = False
                        else:
                            journal_payment_amount_line = self._format(payment_amount_journal,
                                                                       payment_currency) + '*'
                            no_payment = True
                        lines.append({
                            'id': move_line.id,
                            'type': 'line_id',
                            'journal_id': journal_array[i][
                                'journal_id'] if journal_array and not last_journal else False,
                            'total_journal': currency_amount_journal if journal_array and not last_journal else 0.0,
                            'total_journal_in_currency': journal_array[i][
                                'amount'] if journal_array and not last_journal else 0.0,
                            'move_id': move_line.move_id.id or False,
                            'colspan': 0,
                            'name': not first_line and _('Payment Journal') or '',
                            'footnotes': self.env.context['context_id']._get_footnotes('move_line_id', move_line.id),
                            'columns': [number, payment_date, supplier_name, move_line.invoice_id.display_name,
                                        not last_journal and journal_payment_amount_line or ''],
                            'level': 1,
                            'no_payment_line': no_payment,
                        })
                        first_line = True
                        if not last_journal and journal_array:
                            journal_array[i]['show'] = True
                        if i == len(journal_array) - 1 and journal_array:
                            last_journal = True
                        i += 1
                    for journal in filter(lambda x: not x.get('show'), journal_array):
                        supplier_name = not first_line and payment_group.partner_id.name or ''
                        number = not first_line and payment_group.display_name or ''
                        payment_date = not first_line and datetime.strptime(payment_group.payment_date,
                                                                            DEFAULT_SERVER_DATE_FORMAT).strftime(
                            date_format) or None
                        payment_amount_journal = journal['amount']
                        # currency_amount_journal = journal['journal_currency'].compute(payment_amount_journal, used_currency)
                        currency_amount_journal = payment_amount_journal
                        if journal['journal_currency'] != used_currency:
                            currency_amount_journal = currency_amount_journal * payment_group.manual_currency_rate
                        total_amount += currency_amount_journal
                        lines.append({
                            'id': journal['journal_id'],
                            'type': 'line_id',
                            'journal_id': journal['journal_id'],
                            'total_journal': currency_amount_journal,
                            'total_journal_in_currency': journal['amount'],
                            'move_id': False,
                            'colspan': 0,
                            'name': '',
                            'footnotes': {},
                            'columns': [number, payment_date, supplier_name, '',
                                        journal['code'] + ' ' + self._format(
                                            payment_amount_journal, journal['journal_currency'])],
                            'level': 1,
                        })
                        if not move_lines:
                            first_line = True
                    if first_line:
                        lines.append({
                            'id': payment_group.id,
                            'type': 'total',
                            'name': '',
                            'colspan': 0,
                            'style': "border-style: none;",
                            'footnotes': self.env.context['context_id']._get_footnotes(
                                'o_account_reports_domain_total',
                                payment_group.id),
                            'columns': ['', None, '', '',
                                        (self._format(total_amount, used_currency),
                                         "", "border-top:1px solid;")],
                            'level': 1,
                        })
                total_payment_amount += total_amount
                payment_quantity = first_line and payment_quantity + 1 or payment_quantity
        if total_payment_amount:
            if context.get('detail_level') == 'per_supplier':
                columns = [_('Total Payment'), '', None, '', self._format(total_payment_amount, used_currency)]
            else:
                columns = [_('Total Payment'), None, '', '', self._format(total_payment_amount, used_currency)]
            lines.append({
                'id': 0,
                'type': 'total',
                'name': '',
                'colspan': 0,
                'footnotes': {},
                'columns': columns,
                'level': 0,
            })
            lines.append(self._get_line_space('overview'))
        if payment_quantity:
            if context.get('detail_level') == 'per_supplier':
                columns = [_('Total Payment Quantity'), '', None, '', str(payment_quantity)]
            else:
                columns = [_('Total Payment Quantity'), None, '', '', str(payment_quantity)]
            lines.append({
                'id': 0,
                'type': 'total',
                'name': _('Total Payment Quantity'),
                'colspan': 0,
                'footnotes': {},
                'columns': columns,
                'level': 0,
            })

        return lines

    def _get_line_space(self, level, report_type='html'):
        if level == 'per_supplier' and report_type =='html':
            columns = ['', '', None, '', '']
        elif level == 'per_supplier' and report_type =='xlsx':
            columns = ['', '', None, '', '', '']
        else:
            columns = ['', None, '', '', '']
        return {
            'id': 0,
            'type': 'line_id' if report_type == 'xlsx' else 'line',
            'name': '',
            'colspan': 0,
            'footnotes': {},
            'columns': columns,
            'level': 1,
        }

    def get_payment_journal_lines(self, lines):
        total_journal_lines = []
        for journal_line in filter(lambda x: x.get('journal_id', False), lines):
            journal = filter(lambda x: x.get('journal_id', False)
                                       and x.get('journal_id') == journal_line['journal_id'],
                             total_journal_lines)
            if journal:
                journal[0]['total_journal_in_currency'] += journal_line['total_journal_in_currency']
                journal[0]['total_journal'] += journal_line['total_journal']
            else:
                total_journal_lines.append({'journal_id': journal_line['journal_id'],
                                            'journal_name': self.env['account.journal'].browse(
                                                journal_line['journal_id']).name,
                                            'total_journal_in_currency': journal_line['total_journal_in_currency'],
                                            'total_journal': journal_line['total_journal']})
        return total_journal_lines

    def _get_total_amount_xlsx_per_supplier(self, journal_payment):
        total_amout = 0.0
        for journal in journal_payment:
            total_amout += journal['amount']
        return total_amout

    def has_no_payment_lines(self, lines):
        return True if filter(lambda x: x.get('no_payment_line', False), lines) else False

    def _get_domain(self, context, supplier=False):
        state = []
        domain = [('payment_date', '>=', context['date_from']), ('payment_date', '<=', context['date_to']),
                  ('partner_type', '=', 'supplier')]
        if context.get('payment_no'):
            domain += [('name', '=', context.get('payment_no'))]

        if context.get('partner_id') or supplier:
            partner = supplier and supplier or context.get('partner_id')
            domain += [('partner_id', '=', partner)]

        if context.get('analytic_tag_id'):
            domain += [
                ('partner_id.supplier_analytic_tag_ids', 'in', context.get('analytic_tag_id'))]

        if context.get('journal_ids'):
            domain += [
                ('payment_ids.journal_id', 'in', context.get('journal_ids'))]

        if context.get('reference'):
            domain += [
                ('communication', '=', context.get('reference'))]

        if context.get('reference'):
            domain += [
                ('communication', '=', context.get('reference'))]

        if context.get('confirmed', False):
            state.append('confirmed')

        if context.get('posted', False):
            state.append('posted')
        domain += [('state', 'in', state)] if state else [('state', '!=', 'draft')]

        if context.get('company_id'):
            domain += [
                ('company_id', '=', context.get('company_id'))]

        return domain

    @api.model
    def get_title(self):
        return _("Payment Journal")

    @api.model
    def get_name(self):
        return 'payment_journal'

    @api.model
    def get_report_type(self):
        return self.env.ref('receipt_and_payment_journal_report.receipt_payment_journal_report_type')

    def get_template(self):
        return 'receipt_and_payment_journal_report.report_receipt_and_payment_journal'


class PaymentJournalContextReport(models.TransientModel):
    _name = "payment.journal.context.report"
    _description = "A particular context for the payment journal"
    _inherit = "account.report.context.common"

    wizard_id = fields.Integer(string='Payment Journal Wizard')
    payment_no = fields.Char('Payment No')
    journal_ids = fields.Many2many('account.journal', string='Journals')
    partner_id = fields.Many2one('res.partner', 'Supplier')
    analytic_tag_id = fields.Many2one('account.analytic.tag', string='Analytic Tag (From Supplier)')
    reference = fields.Char('Reference')
    confirmed = fields.Boolean('Confirmed')
    posted = fields.Boolean('Posted')
    detail_level = fields.Selection([('per_supplier', 'Per Supplier'), ('overview', 'Overview')], 'Detail Level')
    company_id = fields.Many2one('res.company', 'Company')

    @api.multi
    def get_html_and_data(self, given_context=None):
        if given_context is None:
            given_context = {}
        result = {}
        if given_context:
            if 'force_account' in given_context and (not self.date_from or self.date_from == self.date_to):
                self.date_from = \
                    self.env.user.company_id.compute_fiscalyear_dates(datetime.strptime(self.date_to, "%Y-%m-%d"))[
                        'date_from']
                self.date_filter = 'custom'
            if given_context.get('active_id', False):
                wizard = self.env['receipt.and.payment.journal.report.wizard'].browse(given_context.get('active_id'))
                if wizard and self.wizard_id != wizard.id:
                    self.write({'date_from': wizard.start_date,
                                'date_to': wizard.end_date,
                                'payment_no': wizard.payment_no,
                                'journal_ids': [(6, 0, wizard.journal_ids.ids)],
                                'partner_id': wizard.partner_id.id,
                                'analytic_tag_id': wizard.analytic_tag_id.id,
                                'reference': wizard.reference,
                                'confirmed': wizard.confirmed,
                                'posted': wizard.posted,
                                'detail_level': wizard.detail_level_p,
                                'date_filter': 'custom',
                                'wizard_id': wizard.id,
                                'company_id': wizard.company_id.id,
                                })
        lines = self.get_report_obj().get_lines(self)
        total_payment_journal_lines = self.get_report_obj().get_payment_journal_lines(lines)
        has_payment = self.get_report_obj().has_no_payment_lines(lines)
        rcontext = {
            'res_company': self.env['res.users'].browse(self.env.uid).company_id,
            'context': self.with_context(**given_context),
            'report': self.get_report_obj(),
            'lines': lines,
            'journal_lines': total_payment_journal_lines,
            'footnotes': self.get_footnotes_from_lines(lines),
            'has_payment': has_payment,
            'mode': 'display',
        }
        result['html'] = self.env['ir.model.data'].xmlid_to_object(self.get_report_obj().get_template()).render(
            rcontext)
        result['report_type'] = self.get_report_obj().get_report_type().read(
            ['date_range', 'comparison', 'cash_basis', 'analytic', 'extra_options'])[0]
        select = ['id', 'date_filter', 'date_filter_cmp', 'date_from', 'date_to', 'periods_number', 'date_from_cmp',
                  'date_to_cmp', 'cash_basis', 'all_entries', 'company_ids', 'multi_company', 'hierarchy_3',
                  'analytic']
        if self.get_report_obj().get_name() == 'general_ledger':
            select += ['journal_ids']
            result['available_journals'] = self.get_available_journal_ids_names_and_codes()
        if self.get_report_obj().get_name() == 'partner_ledger':
            select += ['account_type']
        result['report_context'] = self.read(select)[0]
        result['report_context'].update(self._context_add())
        if result['report_type']['analytic']:
            result['report_context']['analytic_account_ids'] = [(t.id, t.name) for t in self.analytic_account_ids]
            result['report_context']['analytic_tag_ids'] = [(t.id, t.name) for t in self.analytic_tag_ids]
            result['report_context'][
                'available_analytic_account_ids'] = self.analytic_manager_id.get_available_analytic_account_ids_and_names()
            result['report_context'][
                'available_analytic_tag_ids'] = self.analytic_manager_id.get_available_analytic_tag_ids_and_names()
        result['xml_export'] = self.env['account.financial.html.report.xml.export'].is_xml_export_available(
            self.get_report_obj())
        result['fy'] = {
            'fiscalyear_last_day': self.env.user.company_id.fiscalyear_last_day,
            'fiscalyear_last_month': self.env.user.company_id.fiscalyear_last_month,
        }
        result['available_companies'] = self.multicompany_manager_id.get_available_company_ids_and_names()
        return result

    def get_report_obj(self):
        return self.env['payment.journal.report']

    def get_columns_names(self):
        return [_("Pay. No"), _("Pay. Date"), _("Supplier"), _("Invoice No"), _("Pay. Amount")]

    def get_per_partner_columns_names(self):
        return [_("Pay. No"), _("Pay. Date"), _("Invoice No"), _("Pay. Amount")]

    def get_per_partner_xlsx_columns_names(self):
        return [_("Supplier"), _("Pay. No"), _("Pay. Date"), _("Invoice No"), _("Pay. Amount"), _("Pay. Total")]

    @api.multi
    def get_columns_types(self):
        return ["text", "date", "text", "text", "text"]

    @api.multi
    def get_per_partner_columns_types(self):
        return ["text", "text", "date", "text", "text"]

    def get_xlsx(self, response):
        output = StringIO.StringIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        report_id = self.get_report_obj()
        sheet = workbook.add_worksheet(report_id.get_title())

        def_style = workbook.add_format({'font_name': 'Arial'})
        title_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2})
        journal_title_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'align': 'center'})
        title_style_right = workbook.add_format({'font_name': 'Arial', 'bold': True,
                                                 'bottom': 2, 'align': 'right'})
        level_0_style = workbook.add_format(
            {'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'pattern': 1, 'font_color': '#FFFFFF'})
        level_0_style_left = workbook.add_format(
            {'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'left': 2, 'pattern': 1,
             'font_color': '#FFFFFF', 'align': 'center'})
        level_0_style_right = workbook.add_format(
            {'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'right': 2, 'pattern': 1,
             'font_color': '#FFFFFF', 'align': 'center'})
        level_1_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2})
        level_1_style_left = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'left': 2})
        level_1_style_right = workbook.add_format(
            {'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'right': 2})
        level_2_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'top': 2})
        level_2_style_left = workbook.add_format({'font_name': 'Arial', 'bold': True, 'top': 2, 'left': 2})
        level_2_style_right = workbook.add_format({'font_name': 'Arial', 'bold': True, 'top': 2, 'right': 2})
        level_3_style = def_style
        level_3_style_left = workbook.add_format({'font_name': 'Arial', 'left': 2})
        level_3_style_right = workbook.add_format({'font_name': 'Arial', 'right': 2})
        domain_style = workbook.add_format({'font_name': 'Arial', 'italic': True})
        domain_style_left = workbook.add_format({'font_name': 'Arial', 'italic': True, 'left': 2})
        domain_style_right = workbook.add_format({'font_name': 'Arial', 'italic': True, 'right': 2, 'align': 'right'})
        domain_style_left_amount = workbook.add_format({'font_name': 'Arial', 'italic': True, 'left': 2,
                                                        'bottom': 2, 'align': 'right'})
        domain_style_right_amount = workbook.add_format({'font_name': 'Arial', 'italic': True, 'right': 2,
                                                         'top': 2, 'align': 'right'})
        upper_line_style = workbook.add_format({'font_name': 'Arial', 'top': 2})
        journal_style_left = workbook.add_format({'font_name': 'Arial', 'italic': True, 'border': 1})
        journal_style_right = workbook.add_format({'font_name': 'Arial', 'italic': True, 'align': 'right', 'border': 1})

        sheet.set_column(0, 0, 50)
        sheet.set_column(1, 0, 20)
        sheet.set_column(2, 0, 40)
        sheet.set_column(3, 0, 30)
        sheet.set_column(4, 0, 20)
        if self.detail_level == 'per_supplier':
            sheet.set_column(1, 0, 50)
            sheet.set_column(2, 0, 20)
            sheet.set_column(5, 0, 15)

        sheet.write(0, 0, '', title_style)

        y_offset = 0
        if self.get_report_obj().get_name() == 'coa' and self.get_special_date_line_names():
            sheet.write(y_offset, 0, '', title_style)
            sheet.write(y_offset, 1, '', title_style)
            x = 2
            for column in self.with_context(is_xls=True).get_special_date_line_names():
                sheet.write(y_offset, x, column, title_style)
                sheet.write(y_offset, x + 1, '', title_style)
                x += 2
            sheet.write(y_offset, x, '', title_style)
            y_offset += 1

        columns_names = self.with_context(is_xls=True).get_columns_names()
        if self.detail_level == 'per_supplier':
            columns_names = self.with_context(is_xls=True).get_per_partner_xlsx_columns_names()

        x = 0
        for column in columns_names:
            if x < len(columns_names) - 1:
                sheet.write(y_offset, x, column.replace('<br/>', ' ').replace('&nbsp;', ' '), title_style)
            else:
                sheet.write(y_offset, x, column.replace('<br/>', ' ').replace('&nbsp;', ' '), title_style_right)
            x += 1
        y_offset += 1

        lines = report_id.with_context(no_format=True, print_mode=True, xlsx_format=True).get_lines(self)
        journal_lines = report_id.with_context(no_format=True, print_mode=True,
                                               xlsx_format=True).get_payment_journal_lines(lines)
        has_payment = report_id.has_no_payment_lines(lines)

        if lines:
            max_width = max([len(l['columns']) for l in lines])

        limit = len(lines)
        for y in range(0, len(lines)):
            if lines[y].get('level') == 0 and lines[y].get('type') == 'line':
                for x in range(0, len(lines[y]['columns']) + 1):
                    sheet.write(y + y_offset, x, None, upper_line_style)
                y_offset += 1
                style_left = level_0_style_left
                style_right = level_0_style_right
                style = level_0_style
            elif lines[y].get('level') == 1 and lines[y].get('type') == 'line':
                for x in range(0, len(lines[y]['columns']) + 1):
                    sheet.write(y + y_offset, x, None, upper_line_style)
                y_offset += 1
                style_left = level_1_style_left
                style_right = level_1_style_right
                style = level_1_style
            elif lines[y].get('level') == 2:
                style_left = level_2_style_left
                style_right = level_2_style_right
                style = level_2_style
            elif lines[y].get('level') == 3:
                style_left = level_3_style_left
                style_right = level_3_style_right
                style = level_3_style
            elif lines[y].get('type') != 'line' and lines[y].get('name') == 'Total':
                style_left = domain_style_left_amount
                style_right = domain_style_right_amount
                style = domain_style
            elif lines[y].get('type') != 'line' and not lines[y].get('name') == 'Total':
                style_left = domain_style_left
                style_right = domain_style_right
                style = domain_style
            else:
                style = def_style
                style_left = def_style
                style_right = def_style
            sheet.write(y + y_offset, 0, lines[y]['name'], style_left)
            for x in xrange(0, max_width - len(lines[y]['columns']) + 1):
                sheet.write(y + y_offset, x, None, style)
            for x in xrange(1, len(lines[y]['columns']) + 1):
                if isinstance(lines[y]['columns'][x - 1], tuple):
                    lines[y]['columns'][x - 1] = lines[y]['columns'][x - 1][0]
                if x < len(lines[y]['columns']):
                    sheet.write(y + y_offset, x + lines[y].get('colspan', 1) - 1, lines[y]['columns'][x - 1], style)
                else:
                    sheet.write(y + y_offset, x + lines[y].get('colspan', 1) - 1, lines[y]['columns'][x - 1],
                                style_right)
            if lines[y]['type'] == 'total' or lines[y].get('level') == 0:
                for x in xrange(0, len(lines[0]['columns'])):
                    sheet.write(y + 1 + y_offset, x, None, upper_line_style)
                y_offset += 1
        if lines:
            for x in xrange(0, max_width):
                sheet.write(len(lines) + y_offset, x, None, upper_line_style)

        limit += 4
        journal_letter_right = 'C'
        total_letter_right = 'E'
        total_letter_left = 'D'
        if self.detail_level == 'per_supplier':
            total_letter_left = 'E'
            journal_letter_right = 'D'
            total_letter_right = 'F'
        sheet.merge_range('A' + str(limit) + ':' + journal_letter_right + str(limit), _('Payment Journal'),
                          level_0_style_left)
        sheet.write(total_letter_left + str(limit), _('Total in Currency'), level_0_style_right)
        sheet.write(total_letter_right + str(limit), _('Total'), level_0_style_right)

        limit += 1

        for journal_line in journal_lines:
            sheet.merge_range('A' + str(limit) + ':' + journal_letter_right + str(limit), journal_line['journal_name'],
                              journal_style_left)
            sheet.write(total_letter_left + str(limit), journal_line['total_journal_in_currency'], journal_style_right)
            sheet.write(total_letter_right + str(limit), journal_line['total_journal'], journal_style_right)
            limit += 1
        limit += 1

        if has_payment:
            sheet.merge_range('A' + str(limit) + ':' + journal_letter_right + str(limit),
                              _('*. This payment does not have any payment line entered yet.'))

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()

    def get_pdf(self):
        if not config['test_enable']:
            self = self.with_context(commit_assetsbundle=True)

        report_obj = self.get_report_obj()
        lines = report_obj.with_context(print_mode=True).get_lines(self)
        journal_lines = report_obj.get_payment_journal_lines(lines)
        footnotes = self.get_footnotes_from_lines(lines)
        has_payment = report_obj.has_no_payment_lines(lines)
        base_url = self.env['ir.config_parameter'].sudo().get_param('report.url') or self.env[
            'ir.config_parameter'].sudo().get_param('web.base.url')
        rcontext = {
            'mode': 'print',
            'base_url': base_url,
            'company': self.env.user.company_id,
        }

        body = self.env['ir.ui.view'].render_template(
            "receipt_and_payment_journal_report.report_receipt_and_payment_journal_letter",
            values=dict(rcontext, lines=lines, journal_lines=journal_lines, has_payment=has_payment,
                        footnotes=footnotes, report=report_obj, context=self),
        )

        header = self.env['report'].render(
            "report.internal_layout",
            values=rcontext,
        )
        header = self.env['report'].render(
            "report.minimal_layout",
            values=dict(rcontext, subst=True, body=header),
        )

        landscape = True

        return self.env['report']._run_wkhtmltopdf([header], [''], [(0, body)], landscape,
                                                   self.env.user.company_id.paperformat_id,
                                                   spec_paperformat_args={'data-report-margin-top': 10,
                                                                          'data-report-header-spacing': 10})

    def get_full_date_names(self, dt_to, dt_from=None):
        res = super(PaymentJournalContextReport, self).get_full_date_names(dt_to, dt_from)
        if dt_from:
            return res.replace('From', 'Period:').replace('to', '-').replace('<br/>', '')

    def get_payment_journals(self, journal_ids):
        if journal_ids:
            journals = ", ".join(journal.code for journal in journal_ids)
            return _('Payment Journals: %s') % journals
        return _('Payment Journals:')

    def get_partner(self, partner_id):
        if partner_id:
            return _('Supplier: %s') % partner_id.name
        return _('Supplier:')

    def get_analytic_tag(self, analytic_tag_id):
        if analytic_tag_id:
            return _('Analytic Tags: %s') % analytic_tag_id.name
        return _('Analytic Tags:')

    def get_status(self, confirmed, posted):
        states = {}
        if confirmed:
            states['confirmed'] = _('Confirmed')
        if posted:
            states['posted'] = _('Posted')
        if states:
            status = ", ".join(value for key, value in states.items())
            return _('Status: %s') % status
        return _('Status:')

    def get_detail_level(self, detail_level):
        return _('Detail Level: %s') % (_('Overview') if detail_level == 'overview' else _('Per Supplier'))
