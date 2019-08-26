# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
##################################################################################

from odoo import models, fields, api, _
from odoo.tools.misc import formatLang
from datetime import datetime, timedelta
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError
from operator import itemgetter
import StringIO
import xlsxwriter
from odoo.tools import config, posix_to_ldml

class CurrenciesVendorLedgerReport(models.AbstractModel):
    _name = "currencies.vendor.ledger.report"
    _description = "Multi Currencies Vendor Ledger Report"
    
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

    def _formatted(self, value, digit):
        formatted = ('%.' + str(digit) + 'f') % value
        return formatted
    
    @api.model
    def get_lines(self, context_id, line_id=None):
        if type(context_id) == int:
            context_id = self.env['currencies.vendor.ledger.context.report'].search([['id', '=', context_id]])
        new_context = dict(self.env.context)
        new_context.update({
            'date_from': context_id.date_from,
            'date_to': context_id.date_to,
            'state': context_id.all_entries and 'all' or 'posted',
            'cash_basis': context_id.cash_basis,
            'context_id': context_id,
            'company_ids': context_id.company_ids.ids,
            'partner_ids':context_id.partners_ids.ids,
        })
        if new_context.get('xlsx_format'):
            res = self.with_context(new_context)._xlsx_lines(line_id)
        else:
            res = self.with_context(new_context)._lines(line_id)
        return res

    @api.model
    def _lines(self, line_id=None):
        ctx = self._context 
        lines = []

        context = self.env.context
        context_id = context.get('context_id')
        partner_ids = context_id.partners_ids.ids or False
        payment_obj = self.env['account.payment']
        
        if not partner_ids:
            partner_ids = context.get('partners_ids',False)
        
        if not partner_ids:
            raise UserError(_('Vendor Not Found'))

        ##############

        unfold_all = context.get('print_mode') and not context['context_id']['partners_ids']
        if not line_id:
            for partner in self.env['res.partner'].browse(partner_ids):
                partner_lines = [{
                    'id': partner.id,
                    'partner_id': partner.id,
                    'type': 'line',
                    'name': partner.name,
                    'footnotes': {},
                    'columns': ['', '', '', '', '', '', '', '', ''],
                    'level': 1,
                    'unfoldable': False,
                    'unfolded': False,
                    # 'colspan': 5,
                }]
                for currency in self.env['res.currency'].search([]):
                    grand_total_debit = 0.0
                    grand_total_credit = 0.0
                    currrency_lines = []
                    globle_dict_list = []
                    total_vendor_invoices = self.env['account.invoice'].search([('partner_id', '=', partner.id),
                                                                                ('type', 'in',
                                                                                 ['in_refund', 'in_invoice']),
                                                                                (
                                                                                'state', 'not in', ['cancel', 'draft']),
                                                                                ('date_invoice', '<',
                                                                                 ctx.get('date_from')),
                                                                                ('currency_id', '=', currency.id)])
                    currrency_lines.append({
                        'id': currency.id,
                        'type': 'line',
                        'name': _('Currency: ') + currency.name,
                        'footnotes': {},
                        'columns': ['', '', '', '', '', '', '', '', ''],
                        'level': 1,
                        'unfoldable': False,
                        'unfolded': False,
                        # 'colspan': 4,
                    })
                    for inv in total_vendor_invoices:
                        if inv.type == 'in_refund':
                            grand_total_debit += inv.amount_total
                        else:
                            grand_total_credit += inv.amount_total

                    total_vendor_payment_group = self.env['account.payment.group'].search(
                        [('partner_id', '=', partner.id),
                         ('partner_type', '=', 'supplier'),
                         ('state', 'not in', ['draft', 'confirmed']),
                         ('payment_date', '<', ctx.get('date_from'))])
                    total_currency_vendor_payment_group = self.filter_currency_customer_payment_group(
                        total_vendor_payment_group, currency)
                    for cpg in total_currency_vendor_payment_group:
                        amount = 0.0
                        payment_line_currency = cpg.payment_ids and cpg.payment_ids[0].currency_id or cpg.currency2_id
                        amount = sum(cpg.payment_ids.mapped('amount'))

                        if payment_line_currency.id != currency.id and cpg.manual_currency_rate:
                            if currency.id != self.env.user.company_id.currency_id.id:
                                amount = amount / cpg.manual_currency_rate
                            else:
                                amount = amount * cpg.manual_currency_rate
                            # amount = amount / cpg.manual_currency_rate
                        grand_total_debit += amount

                    grand_total_balance = grand_total_debit - grand_total_credit

                    currrency_lines.append({
                        'id': currency.id,
                        'type': 'o_account_reports_domain_total',
                        'name': _("Initial Balance"),
                        'footnotes': {},
                        'columns': ['', '', '', '', '', '', self._format(grand_total_debit, currency),
                                    self._format(grand_total_credit, currency),
                                    self._format(grand_total_balance, currency)],
                        'level': 0,
                    })

                    ##############

                    balance = grand_total_balance
                    total_debit = grand_total_debit
                    total_credit = grand_total_credit

                    vendor_invoices = self.env['account.invoice'].search([('partner_id', '=', partner.id),
                                                                          ('type', 'in', ['in_refund', 'in_invoice']),
                                                                          ('state', 'not in', ['cancel', 'draft']),
                                                                          ('date_invoice', '>=', ctx.get('date_from')),
                                                                          ('date_invoice', '<=', ctx.get('date_to')),
                                                                          ('currency_id', '=', currency.id)],
                                                                         order='date_invoice')
                    for inv in vendor_invoices:
                        debit = credit = 0.0
                        if inv.type == 'in_refund':
                            debit = inv.amount_total
                        else:
                            credit = inv.amount_total

                        globle_dict_list.append({
                            'obj': inv,
                            'date': inv.date_invoice,
                            'custom_type': 'invoice',
                            'doc_type': inv.journal_document_type_id.display_name,
                            'number': inv.display_name,
                            'reference': inv.name,
                            'debit': debit,
                            'credit': credit,
                            'currency_rate': inv.manual_currency_rate,
                            'amount_in_currency': debit if inv.type == "in_refund" else credit,
                        })

                    vendor_payment_group = self.env['account.payment.group'].search([('partner_id', '=', partner.id),
                                                                                     ('partner_type', '=', 'supplier'),
                                                                                     ('state', 'not in',
                                                                                      ['draft', 'confirmed']),
                                                                                     ('payment_date', '>=',
                                                                                      ctx.get('date_from')),
                                                                                     ('payment_date', '<=',
                                                                                      ctx.get('date_to'))],
                                                                                    order='payment_date')

                    currency_vendor_payment_group = self.filter_currency_customer_payment_group(vendor_payment_group,
                                                                                                currency)
                    if currency_vendor_payment_group or vendor_invoices:
                        if not filter(lambda x: x.get('partner_id') and x.get('partner_id') == partner.id, lines):
                            lines.extend(partner_lines)
                        lines.extend(currrency_lines)
                    for cpg in currency_vendor_payment_group:
                        payment_amount = 0.0
                        payment_line_currency = cpg.currency2_id
                        for pay in cpg.payment_ids:
                            payment_amount += pay.amount or 0.0
                            payment_line_currency = pay.currency_id

                        debit = payment_amount
                        amount_in_currency = payment_amount
                        credit = 0.0
                        if cpg.manual_currency_rate and payment_line_currency.id != currency.id:
                            if currency.id != self.env.user.company_id.currency_id.id:
                                debit = debit / cpg.manual_currency_rate
                            else:
                                debit = debit * cpg.manual_currency_rate

                        # if payment_line_currency.id != currency.id and cpg.manual_currency_rate:
                        #     debit = debit / cpg.manual_currency_rate

                        globle_dict_list.append({
                            'obj': cpg,
                            'custom_type': 'payment',
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
                        if dict.get('custom_type') == 'payment':
                            total_credit += dict['credit']
                            total_debit += dict['debit']
                            balance += dict['debit'] - dict['credit']
                            move_id = dict['obj'].move_line_ids and dict['obj'].move_line_ids[0].move_id \
                                      and dict['obj'].move_line_ids and dict['obj'].move_line_ids[0].move_id.id or False

                            if len(dict['number']) > 20:
                                dict['number'] = dict['number'][:19] + "..."
                            if len(dict['reference']) > 20:
                                dict['reference'] = dict['reference'][:19] + "..."

                            vals = {
                                'type': 'payment',
                                'unfoldable': True,
                                'name':dict['number'],
                                'payment_group': dict['obj'].id,
                                'move_id': move_id,
                            }

                            if not payment_obj.search([('state', 'not in', ['draft']), ('partner_id', '=', partner.id),
                                                       ('payment_group_id', '=', dict['obj'].id)]):
                                vals.update({
                                    'type': 'move_line_id',
                                    'name': dict['number'],
                                    'move_id': move_id,
                                    'action': dict['obj'].open_payment_group_from_report(),
                                    'unfoldable': False,
                                    'level': 1,
                                })

                            vals.update({
                                'id': dict['obj'].id,
                                'unfolded': dict['obj'] and (
                                    dict['obj'].id in context['context_id']['unfolded_payments'].ids) or False,
                                'action': dict['obj'].open_payment_group_from_report(),
                                'footnotes': self.env.context['context_id']._get_footnotes(vals['type'], dict['obj'].id),
                                'columns': [dict['date'], dict['doc_type'], dict['number'], dict['reference'],
                                            self._formatted(dict['currency_rate'], 6),
                                            self._format(dict['amount_in_currency'],
                                                         dict['payment_currency']),
                                            self._format(dict['debit'], currency),
                                            self._format(dict['credit'], currency), self._format(balance, currency)],
                                'level': 0,
                            })

                            lines.append(vals)
                            if dict['obj'].id in context['context_id']['unfolded_payments'].ids:
                                lines = self.get_account_payment_line(dict['obj'].id, lines)

                        elif dict.get('custom_type') == 'invoice':
                            total_credit += dict['credit']
                            total_debit += dict['debit']
                            balance += dict['debit'] - dict['credit']
                            lines.append({
                                'id': dict['obj'].id,
                                'type': 'move_line_id',
                                'move_id': dict['obj'].move_id.id,
                                'name': dict['number'],
                                'action': dict['obj'].open_invoice_from_report(),
                                'footnotes': self.env.context['context_id']._get_footnotes('move_line_id',
                                                                                           dict['obj'].id),
                                'level': 0,
                                'columns': [dict['date'], dict['doc_type'], dict['number'], dict['reference'],
                                            self._formatted(dict['currency_rate'], 6),
                                            self._format(dict['amount_in_currency'], currency),
                                            self._format(dict['debit'], currency),
                                            self._format(dict['credit'], currency), self._format(balance, currency)],
                            })
                    if sorted_globle_dict_list:
                        lines.append({
                            'id': currency.id,
                            'type': 'o_account_reports_domain_total',
                            'name': _("Total Currency: ") + currency.name,
                            'footnotes': self.env.context['context_id']._get_footnotes('o_account_reports_domain_total',
                                                                                       currency.id),
                            'columns': ['', '', '', '', '', '', self._format(total_debit, currency),
                                        self._format(total_credit, currency), self._format(balance, currency)],
                            'level': 0,
                            'unfoldable': False,
                        })
                        lines.append({
                            'id': 0,
                            'type': 'line',
                            'name': '',
                            'footnotes': {},
                            'columns': ['', '', '', '', '', '', '', '', ''],
                            'level': 1,
                            'unfoldable': False,
                            'unfolded': False,
                        })
        else:
            domain_lines = []
            lines = self.get_account_payment_line(line_id, domain_lines, unfolded=True)
            
        return lines

    @api.model
    def _xlsx_lines(self, line_id=None):
        ctx = self._context
        lines = []

        context = self.env.context
        context_id = context.get('context_id')
        partner_ids = context_id.partners_ids.ids or False
        payment_obj = self.env['account.payment']

        if not partner_ids:
            partner_ids = context.get('partners_ids', False)

        if not partner_ids:
            raise UserError(_('Vendor Not Found'))

        ##############

        unfold_all = context.get('print_mode') and not context['context_id']['partners_ids']
        if not line_id:
            for partner in self.env['res.partner'].browse(partner_ids):
                partner_lines = [{
                    'id': partner.id,
                    'partner_id': partner.id,
                    'type': 'line',
                    'name': partner.name,
                    'footnotes': {},
                    'columns': ['', '', '', '', '', '', '', '', ''],
                    'level': 1,
                    'unfoldable': False,
                    'unfolded': False,
                    # 'colspan': 5,
                }]
                for currency in self.env['res.currency'].search([]):
                    grand_total_debit = 0.0
                    grand_total_credit = 0.0
                    currrency_lines = []
                    globle_dict_list = []
                    total_vendor_invoices = self.env['account.invoice'].search([('partner_id', '=', partner.id),
                                                                                ('type', 'in',
                                                                                 ['in_refund', 'in_invoice']),
                                                                                (
                                                                                    'state', 'not in',
                                                                                    ['cancel', 'draft']),
                                                                                ('date_invoice', '<',
                                                                                 ctx.get('date_from')),
                                                                                ('currency_id', '=', currency.id)])
                    currrency_lines.append({
                        'id': currency.id,
                        'type': 'line',
                        'name': _('Currency: ') + currency.name,
                        'footnotes': {},
                        'columns': ['', '', '', '', '', ''],
                        'level': 1,
                        'unfoldable': False,
                        'unfolded': False,
                        'colspan': 4,
                    })
                    for inv in total_vendor_invoices:
                        if inv.type == 'in_refund':
                            grand_total_debit += inv.amount_total
                        else:
                            grand_total_credit += inv.amount_total

                    total_vendor_payment_group = self.env['account.payment.group'].search(
                        [('partner_id', '=', partner.id),
                         ('partner_type', '=', 'supplier'),
                         ('state', 'not in', ['draft', 'confirmed']),
                         ('payment_date', '<', ctx.get('date_from'))])
                    total_currency_vendor_payment_group = self.filter_currency_customer_payment_group(
                        total_vendor_payment_group, currency)
                    for cpg in total_currency_vendor_payment_group:
                        amount = 0.0
                        payment_line_currency = cpg.payment_ids and cpg.payment_ids[0].currency_id or cpg.currency2_id
                        amount = sum(cpg.payment_ids.mapped('amount'))

                        if payment_line_currency.id != currency.id and cpg.manual_currency_rate:
                            if currency.id != self.env.user.company_id.currency_id.id:
                                amount = amount / cpg.manual_currency_rate
                            else:
                                amount = amount * cpg.manual_currency_rate
                            # amount = amount / cpg.manual_currency_rate
                        grand_total_debit += amount

                    grand_total_balance = grand_total_debit - grand_total_credit

                    currrency_lines.append({
                        'id': currency.id,
                        'type': 'o_account_reports_domain_total',
                        'name': _("Initial Balance"),
                        'footnotes': {},
                        'columns': ['', '', '', '', '', '', self._format(grand_total_debit, currency),
                                    self._format(grand_total_credit, currency),
                                    self._format(grand_total_balance, currency)],
                        'level': 1,
                    })

                    ##############

                    balance = grand_total_balance
                    total_debit = grand_total_debit
                    total_credit = grand_total_credit

                    vendor_invoices = self.env['account.invoice'].search([('partner_id', '=', partner.id),
                                                                          ('type', 'in', ['in_refund', 'in_invoice']),
                                                                          ('state', 'not in', ['cancel', 'draft']),
                                                                          ('date_invoice', '>=', ctx.get('date_from')),
                                                                          ('date_invoice', '<=', ctx.get('date_to')),
                                                                          ('currency_id', '=', currency.id)],
                                                                         order='date_invoice')
                    for inv in vendor_invoices:
                        debit = credit = 0.0
                        if inv.type == 'in_refund':
                            debit = inv.amount_total
                        else:
                            credit = inv.amount_total

                        globle_dict_list.append({
                            'obj': inv,
                            'date': inv.date_invoice,
                            'custom_type': 'invoice',
                            'doc_type': inv.journal_document_type_id.display_name,
                            'number': inv.display_name,
                            'reference': inv.name,
                            'debit': debit,
                            'credit': credit,
                            'currency_rate': inv.manual_currency_rate,
                            'amount_in_currency': debit if inv.type == "in_refund" else credit,
                        })

                    vendor_payment_group = self.env['account.payment.group'].search([('partner_id', '=', partner.id),
                                                                                     ('partner_type', '=', 'supplier'),
                                                                                     ('state', 'not in',
                                                                                      ['draft', 'confirmed']),
                                                                                     ('payment_date', '>=',
                                                                                      ctx.get('date_from')),
                                                                                     ('payment_date', '<=',
                                                                                      ctx.get('date_to'))],
                                                                                    order='payment_date')

                    currency_vendor_payment_group = self.filter_currency_customer_payment_group(vendor_payment_group,
                                                                                                currency)
                    if currency_vendor_payment_group or vendor_invoices:
                        if not filter(lambda x: x.get('partner_id') and x.get('partner_id') == partner.id, lines):
                            lines.extend(partner_lines)
                        lines.extend(currrency_lines)
                    for cpg in currency_vendor_payment_group:
                        payment_amount = 0.0
                        payment_line_currency = cpg.currency2_id
                        for pay in cpg.payment_ids:
                            payment_amount += pay.amount or 0.0
                            payment_line_currency = pay.currency_id

                        debit = payment_amount
                        amount_in_currency = payment_amount
                        credit = 0.0
                        if cpg.manual_currency_rate and payment_line_currency.id != currency.id:
                            if currency.id != self.env.user.company_id.currency_id.id:
                                debit = debit / cpg.manual_currency_rate
                            else:
                                debit = debit * cpg.manual_currency_rate

                        # if payment_line_currency.id != currency.id and cpg.manual_currency_rate:
                        #     debit = debit / cpg.manual_currency_rate

                        globle_dict_list.append({
                            'obj': cpg,
                            'custom_type': 'payment',
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
                        if dict.get('custom_type') == 'payment':
                            total_credit += dict['credit']
                            total_debit += dict['debit']
                            balance += dict['debit'] - dict['credit']
                            move_id = dict['obj'].move_line_ids and dict['obj'].move_line_ids[0].move_id \
                                      and dict['obj'].move_line_ids and dict['obj'].move_line_ids[0].move_id.id or False

                            if len(dict['number']) > 20:
                                dict['number'] = dict['number'][:19] + "..."
                            if len(dict['reference']) > 20:
                                dict['reference'] = dict['reference'][:19] + "..."

                            vals = {
                                'type': 'payment',
                                'unfoldable': True,
                                'name': dict['number'],
                                'payment_group': dict['obj'].id,
                                'move_id': move_id,
                            }

                            if not payment_obj.search([('state', 'not in', ['draft']), ('partner_id', '=', partner.id),
                                                       ('payment_group_id', '=', dict['obj'].id)]):
                                vals.update({
                                    'type': 'move_line_id',
                                    'name': dict['number'],
                                    'move_id': move_id,
                                    'action': dict['obj'].open_payment_group_from_report(),
                                    'unfoldable': False,
                                    'level': 1,
                                })

                            vals.update({
                                'id': dict['obj'].id,
                                'unfolded': dict['obj'] and (
                                    dict['obj'].id in context['context_id']['unfolded_payments'].ids) or False,
                                'action': dict['obj'].open_payment_group_from_report(),
                                'footnotes': self.env.context['context_id']._get_footnotes(vals['type'],
                                                                                           dict['obj'].id),
                                'columns': [dict['date'], dict['doc_type'] or '', dict['number'], dict['reference'] or '',
                                            self._formatted(dict['currency_rate'], 6),
                                            self._format(dict['amount_in_currency'],
                                                         dict['payment_currency']),
                                            self._format(dict['debit'], currency),
                                            self._format(dict['credit'], currency), self._format(balance, currency)],
                                'level': 2,
                            })

                            lines.append(vals)
                            if dict['obj'].id in context['context_id']['unfolded_payments'].ids:
                                lines = self.get_account_payment_line(dict['obj'].id, lines)

                        elif dict.get('custom_type') == 'invoice':
                            total_credit += dict['credit']
                            total_debit += dict['debit']
                            balance += dict['debit'] - dict['credit']
                            lines.append({
                                'id': dict['obj'].id,
                                'type': 'move_line_id',
                                'move_id': dict['obj'].move_id.id,
                                'name': dict['number'],
                                'action': dict['obj'].open_invoice_from_report(),
                                'footnotes': self.env.context['context_id']._get_footnotes('move_line_id',
                                                                                           dict['obj'].id),
                                'level': 2,
                                'columns': [dict['date'], dict['doc_type'] or '', dict['number'], dict['reference'] or '',
                                            self._formatted(dict['currency_rate'], 6),
                                            self._format(dict['amount_in_currency'], currency),
                                            self._format(dict['debit'], currency),
                                            self._format(dict['credit'], currency), self._format(balance, currency)],
                            })
                    if sorted_globle_dict_list:
                        lines.append({
                            'id': currency.id,
                            'type': 'o_account_reports_domain_total',
                            'name': _("Total Currency: ") + currency.name,
                            'footnotes': self.env.context['context_id']._get_footnotes('o_account_reports_domain_total',
                                                                                       currency.id),
                            'columns': ['', '', '', '', '', '', self._format(total_debit, currency),
                                        self._format(total_credit, currency), self._format(balance, currency)],
                            'level': 2,
                            'unfoldable': False,
                        })
                    if sorted_globle_dict_list:
                        lines.append({
                            'id': 0,
                            'type': 'o_account_reports_domain_total',
                            'name': '',
                            'footnotes': {},
                            'columns': ['', '', '', '', '', '', '', '', ''],
                            'level': 1,
                            'unfoldable': False,
                            'unfolded': False,
                        })
        else:
            domain_lines = []
            lines = self.get_account_payment_line(line_id, domain_lines, unfolded=True)

        return lines


    def get_account_payment_line(self, line_id, lines, unfolded=None):
        if unfolded:
            lines.append({
                'level': 1,
                'unfoldable': False,
                'footnotes': {},
                'columns': ["Date", "Doc Type", "Number", "Reference", "Exchange Rate", "Amount in Currency",
                            "Debit", "Credit", "Balance"],
                'type': 'line',
                'name': "",
                'id': 0,
            })
        payment_group_line = self.env['account.payment.group'].browse(line_id)
        line_currency = self.get_currency_section(payment_group_line)

        payment_total_debit = 0.0
        payment_total_credit = 0.0
        payment_total_balance = 0.0
        #
        for payment in payment_group_line.payment_ids:
            name = payment.display_name or ""
            if payment_group_line.unmatched_amount:
                name = _("Advance")
                debit = payment.unmatched_amount and payment.unmatched_amount or payment.amount
                currency_amount = debit
                credit = 0.0
                if payment.currency_id.id != line_currency.id and payment_group_line.manual_currency_rate:
                    if line_currency.id != self.env.user.company_id.currency_id.id:
                        debit = debit / payment_group_line.manual_currency_rate
                    else:
                        debit = debit * payment_group_line.manual_currency_rate
                    # debit = debit / payment_group_line.manual_currency_rate
                balance = debit - credit

                payment_total_debit += debit
                payment_total_credit += credit
                payment_total_balance += balance

                move_id = payment.move_line_ids and payment.move_line_ids[0].move_id \
                          and payment.move_line_ids and payment.move_line_ids[0].move_id.id or False
                invoice_number = payment.display_name

                lines.append({
                    'id': payment.id,
                    'type': 'move_line_id',
                    'action': payment_group_line.open_payment_group_from_report(),
                    'move_id': move_id,
                    'unfoldable': False,
                    'name': name,
                    'footnotes': {},
                    'columns': [payment.payment_date, payment.receiptbook_id.display_name, invoice_number, '',
                                self._formatted(payment_group_line.manual_currency_rate, 6),
                                self._format(currency_amount, payment.currency_id),
                                self._format(debit, line_currency), self._format(credit, line_currency),
                                self._format(balance, line_currency)],
                    'level': 1,
                    'unfoldable': False,
                })
        payment_line_currency = payment_group_line.payment_ids and payment_group_line.payment_ids[0].currency_id \
                                or payment_group_line.currency2_id
        for aml in payment_group_line.matched_move_line_ids:
            credit = 0.0
            debit = aml.with_context(payment_group_id=payment_group_line.id).payment_group_matched_amount
            currency_amount = aml.with_context(payment_group_id=payment_group_line.id).payment_group_matched_amount

            if payment_line_currency.id != self.env.user.company_id.currency_id.id \
                    and line_currency.id != self.env.user.company_id.currency_id.id:
                debit = currency_amount = aml.with_context(
                    payment_group_id=payment_group_line.id).payment_group_matched_amount_currency
            if payment_line_currency.id != line_currency.id and payment_group_line.manual_currency_rate:
                if line_currency.id == self.env.user.company_id.currency_id.id:
                    currency_amount = currency_amount / payment_group_line.manual_currency_rate
                else:
                    debit = debit / payment_group_line.manual_currency_rate

            # if payment_line_currency.id != line_currency.id and payment_group_line.manual_currency_rate:
            #     debit = debit / payment_group_line.manual_currency_rate

            balance = debit - credit

            payment_total_debit += debit
            payment_total_credit += credit
            payment_total_balance += balance

            move_id = aml.move_id.id or False
            invoice_number = aml.invoice_id.display_name

            lines.append({
                'id': aml.id,
                'type': 'move_line_id',
                'action': payment_group_line.open_payment_group_from_report(),
                'move_id': move_id,
                'unfoldable': False,
                'name': invoice_number,
                'footnotes': {},
                'columns': [aml.date, payment_group_line.receiptbook_id.display_name, invoice_number, '',
                            self._formatted(payment_group_line.manual_currency_rate, 6),
                            self._format(currency_amount, payment_line_currency),
                            self._format(debit, line_currency), self._format(credit, line_currency),
                            self._format(balance, line_currency)],
                'level': 1,
                'unfoldable': False,
            })

        lines.append({
            'id': payment.id,
            'type': 'o_account_reports_domain_total',
            'name': "Total",
            'footnotes': self.env.context['context_id']._get_footnotes('o_account_reports_domain_total',
                                                                       payment.id),
            'columns': ['', '', '', '', '', '', self._format(payment_total_debit, line_currency),
                        self._format(payment_total_credit, line_currency),
                        self._format(payment_total_balance, line_currency)],
            'level': 3,
            'unfoldable': False,
        })
        return lines

    def filter_currency_customer_payment_group(self, vendor_payment_group, currency):
        filter_currency_payment_group = vendor_payment_group.filtered(
            lambda x: x.mapped('matched_move_line_ids').filtered(
                lambda i: i.invoice_id and i.invoice_id.currency_id.id == currency.id)
                      or (not x.matched_move_line_ids and x.unmatched_amount and x.mapped('payment_ids').filtered(
                lambda p: p.currency_id and p.currency_id.id == currency.id)))
        return filter_currency_payment_group

    def get_currency_section(self, payment_group_line):
        if payment_group_line.matched_move_line_ids:
            filter_payment = payment_group_line.matched_move_line_ids.filtered(lambda i: i.invoice_id)
            if filter_payment:
                return filter_payment[0].invoice_id.currency_id
        else:
            if payment_group_line.unmatched_amount and payment_group_line.payment_ids:
                return payment_group_line.payment_ids[0].currency_id
    
    @api.model
    def get_title(self):
        return _("Multi Currencies Vendor Ledger Report")
    
    @api.model
    def get_name(self):
        return 'currencies_vendor_ledger_report'
        
    @api.model
    def get_report_type(self):
        return self.env.ref('bi_partner_transaction_report.currencies_partner_ledger_report_type')
    
    def get_template(self):
        return 'bi_partner_transaction_report.report_financial_bi_partner'

 
        
class CurrenciesVendorLedgerContextReport(models.TransientModel):
    _name = "currencies.vendor.ledger.context.report"
    _description = "A particular context for the Partner Transaction"
    _inherit = "account.report.context.common"

    partners_ids = fields.Many2many('res.partner', 'vendor_ledger_to_partners', string='Unfolded lines')
    fold_field = 'unfolded_payments'
    unfolded_payments = fields.Many2many('account.payment.group', 'currencies_vendor_context_to_payment',
                                         string='Unfolded lines')
    wizard_id = fields.Integer(string='Customer Wizard')
    

    def get_report_obj(self):
        return self.env['currencies.vendor.ledger.report']

    def get_columns_names(self):
        return [_("Date"), _("Doc Type"), _("Number"), _("Reference"), _("Manual Rate"), _("Amount in Currency"), _("Debit"), _("Credit"), _("Balance")]

    @api.multi
    def get_columns_types(self):
        return ["date", "text", "text", "text", "number", "number", "number", "number", "number"]

    def get_xlsx(self, response):
        output = StringIO.StringIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        report_id = self.get_report_obj()
        if len(report_id.get_title()) > 31:
            title = report_id.get_title()[:25]
        else:
            title = report_id.get_title()
        sheet = workbook.add_worksheet(title)

        def_style = workbook.add_format({'font_name': 'Arial'})
        title_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2})
        level_0_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'pattern': 1, 'font_color': '#FFFFFF'})
        level_0_style_left = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'left': 2, 'pattern': 1, 'font_color': '#FFFFFF'})
        level_0_style_right = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'right': 2, 'pattern': 1, 'font_color': '#FFFFFF'})
        level_1_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2})
        level_1_style_left = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'left': 2})
        level_1_style_right = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'right': 2})
        level_2_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'top': 2})
        level_2_style_left = workbook.add_format({'font_name': 'Arial', 'bold': True, 'top': 2, 'left': 2})
        level_2_style_right = workbook.add_format({'font_name': 'Arial', 'bold': True, 'top': 2, 'right': 2})
        level_3_style = def_style
        level_3_style_left = workbook.add_format({'font_name': 'Arial', 'left': 2})
        level_3_style_right = workbook.add_format({'font_name': 'Arial', 'right': 2})
        domain_style = workbook.add_format({'font_name': 'Arial', 'italic': True})
        domain_style_left = workbook.add_format({'font_name': 'Arial', 'italic': True, 'left': 2})
        domain_style_right = workbook.add_format({'font_name': 'Arial', 'italic': True, 'right': 2})
        upper_line_style = workbook.add_format({'font_name': 'Arial', 'top': 2})

        sheet.set_column(0, 0, 15) #  Set the first column width to 15

        sheet.write(0, 0, '', title_style)

        y_offset = 0
        if self.get_report_obj().get_name() == 'coa' and self.get_special_date_line_names():
            sheet.write(y_offset, 0, '', title_style)
            sheet.write(y_offset, 1, '', title_style)
            x = 2
            for column in self.with_context(is_xls=True).get_special_date_line_names():
                sheet.write(y_offset, x, column, title_style)
                sheet.write(y_offset, x+1, '', title_style)
                x += 2
            sheet.write(y_offset, x, '', title_style)
            y_offset += 1

        x = 1
        for column in self.with_context(is_xls=True).get_columns_names():
            sheet.write(y_offset, x, column.replace('<br/>', ' ').replace('&nbsp;',' '), title_style)
            x += 1
        y_offset += 1

        lines = report_id.with_context(no_format=True, print_mode=True, xlsx_format=True).get_lines(self)

        if lines:
            max_width = max([len(l['columns']) for l in lines])

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
            elif lines[y].get('type') != 'line':
                style_left = domain_style_left
                style_right = domain_style_right
                style = domain_style
            else:
                style = def_style
                style_left = def_style
                style_right = def_style
            sheet.write(y + y_offset, 0, lines[y]['name'], style_left)
            for x in xrange(1, max_width - len(lines[y]['columns']) + 1):
                sheet.write(y + y_offset, x, None, style)
            for x in xrange(1, len(lines[y]['columns']) + 1):
                if isinstance(lines[y]['columns'][x - 1], tuple):
                    lines[y]['columns'][x - 1] = lines[y]['columns'][x - 1][0]
                if x < len(lines[y]['columns']):
                    sheet.write(y + y_offset, x+lines[y].get('colspan', 1)-1, lines[y]['columns'][x - 1], style)
                else:
                    sheet.write(y + y_offset, x+lines[y].get('colspan', 1)-1, lines[y]['columns'][x - 1], style_right)
            if lines[y]['type'] == 'total' or lines[y].get('level') == 0:
                for x in xrange(0, len(lines[0]['columns']) + 1):
                    sheet.write(y + 1 + y_offset, x, None, upper_line_style)
                y_offset += 1
        if lines:
            for x in xrange(0, max_width+1):
                sheet.write(len(lines) + y_offset, x, None, upper_line_style)

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()


    def get_pdf(self):
        if not config['test_enable']:
            self = self.with_context(commit_assetsbundle=True)

        report_obj = self.get_report_obj()
        lines = report_obj.with_context(print_mode=True).get_lines(self)
        footnotes = self.get_footnotes_from_lines(lines)
        base_url = self.env['ir.config_parameter'].sudo().get_param('report.url') or self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        rcontext = {
            'mode': 'print',
            'base_url': base_url,
            'company': self.env.user.company_id,
        }

        body = self.env['ir.ui.view'].render_template(
            "bi_partner_transaction_report.report_financial_letter_bi_partner",
            values=dict(rcontext, lines=lines, footnotes=footnotes, report=report_obj, context=self),
        )

        header = self.env['report'].render(
            "report.internal_layout",
            values=rcontext,
        )
        header = self.env['report'].render(
            "report.minimal_layout",
            values=dict(rcontext, subst=True, body=header),
        )

        landscape = False
        if len(self.get_columns_names()) > 4:
            landscape = True

        return self.env['report']._run_wkhtmltopdf([header], [''], [(0, body)], landscape, self.env.user.company_id.paperformat_id, spec_paperformat_args={'data-report-margin-top': 10, 'data-report-header-spacing': 10})

