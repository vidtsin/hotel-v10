# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import json
from odoo.tools import float_is_zero, float_compare
from odoo import fields, models, api, _
from odoo.exceptions import UserError, Warning


class account_invoice_line(models.Model):
    _inherit = 'account.invoice.line'

    @api.onchange('product_id')
    def _onchange_product_id(self):
        domain = {}
        if self.product_id:
            if not self.invoice_id:
                return
            res = super(account_invoice_line, self)._onchange_product_id()
            if self.invoice_id.manual_currency_rate_active and self.invoice_id.currency_id != self.invoice_id.company_id.currency_id:
                if self.invoice_id.manual_currency_rate <= 0.00:
                    raise Warning(_('Please enter currency rate grater than 0 or positive number'))
                if self.invoice_id.type in ('out_invoice', 'out_refund'):
                    taxes = self.product_id.taxes_id or self.account_id.tax_ids
                else:
                    taxes = self.product_id.supplier_taxes_id or self.account_id.tax_ids
                company_id = self.company_id or self.env.user.company_id
                taxes = taxes.filtered(lambda r: r.company_id == company_id)
                self.invoice_line_tax_ids = False
                self.invoice_line_tax_ids = self.invoice_id.fiscal_position_id.map_tax(taxes, self.product_id,
                                                                                       self.invoice_id.partner_id)
                if self.invoice_id.type == 'out_invoice':
                    manual_currency_rate = self.product_id.lst_price / self.invoice_id.manual_currency_rate
                else:
                    manual_currency_rate = self.product_id.standard_price / self.invoice_id.manual_currency_rate
                self.price_unit = manual_currency_rate
                self.name = self.product_id.name
            return res


# WATCH OUT, it is overriding the std function
class account_invoice(models.Model):
    _inherit = 'account.invoice'

    manual_currency_rate_active = fields.Boolean('Apply Manual Exchange')
    manual_currency_rate = fields.Float('Inverse Rate', digits=(12, 6))
    currency_rate = fields.Float(compute='_compute_currency_rate',  string='Currency Rate', copy=False,
                                 store=True, digits=(16, 4))

    @api.depends('date', 'currency_id', 'manual_currency_rate_active', 'manual_currency_rate')
    def _compute_currency_rate(self):
        for record in self:
            record.currency_rate = record._get_currency_rate()

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        super(account_invoice, self)._onchange_journal_id()
        purchase_ids = self.invoice_line_ids.mapped('purchase_id')
        if purchase_ids:
            keep_exchange_rate = self.env['ir.values'].get_default('purchase.config.settings', 'keep_exchange_rate')
            orders = purchase_ids.filtered('manual_currency_rate_active')
            if keep_exchange_rate and orders:
                self.currency_id = orders and orders[0].currency_id.id or False

    @api.model
    def default_get(self, fields):
        res = super(account_invoice, self).default_get(fields)
        if res.get('purchase_id', False):
            order = self.env['purchase.order'].browse(res.get('purchase_id'))
            keep_exchange_rate = self.env['ir.values'].get_default('purchase.config.settings', 'keep_exchange_rate')
            if keep_exchange_rate and order.manual_currency_rate_active:
                res.update({'currency_id': order.currency_id.id})
                res.update({'manual_currency_rate_active': order.manual_currency_rate_active})
                res.update({'manual_currency_rate': order.manual_currency_rate})
        return res

    @api.multi
    def check_manual_currency_rate(self):
        keep_exchange_rate_sale = self.env['ir.values'].get_default('sale.config.settings', 'keep_exchange_rate')
        keep_exchange_rate_purchse = self.env['ir.values'].get_default('purchase.config.settings', 'keep_exchange_rate')
        for rec in self:
            orders = rec.invoice_line_ids.mapped('sale_line_ids').mapped('order_id')
            if orders and keep_exchange_rate_sale:
                if orders.filtered(
                        lambda o: o.manual_currency_rate_active and (
                                    o.manual_currency_rate != rec.manual_currency_rate)):
                    raise Warning(_('The manual currency rate must be the same from Quotations to Invoices'))
                if orders.filtered(lambda o: o.currency_id != rec.currency_id):
                    raise Warning(_('The currency must be the same from Quotations to Invoices'))
            p_orders = rec.invoice_line_ids.mapped('purchase_id')
            if p_orders and keep_exchange_rate_purchse:
                if p_orders.filtered(
                        lambda o: o.manual_currency_rate_active and (
                                    o.manual_currency_rate != rec.manual_currency_rate)):
                    raise Warning(_('The manual currency rate must be the same from Quotations to Invoices'))
                if p_orders.filtered(lambda o: o.currency_id != rec.currency_id):
                    raise Warning(_('The currency must be the same from Quotations to Invoices'))

    @api.multi
    def get_localization_invoice_vals(self):
        self.ensure_one()
        res = super(account_invoice, self).get_localization_invoice_vals()
        if self.localization == 'argentina':
            if 'currency_rate' in res:
                res['currency_rate'] = self._get_currency_rate()
        return res

    @api.multi
    def action_invoice_open(self):
        self.check_manual_currency_rate()
        return super(account_invoice, self).action_invoice_open()

    @api.multi
    def action_move_create(self):
        """ Creates invoice related analytics and financial move lines """
        res = super(account_invoice, self).action_move_create()
        account_move = self.env['account.move']
        price = False
        for inv in self:

            # if inv.manual_currency_rate_active and inv.currency_id != inv.company_id.currency_id:
            if inv.currency_id != inv.company_id.currency_id:
                inv.move_id.write({'state': 'draft'})
                inv.move_id.line_ids = False

                ctx = dict(self._context, lang=inv.partner_id.lang)
                if not inv.date_invoice:
                    inv.with_context(ctx).write({'date_invoice': fields.Date.context_today(self)})
                date_invoice = inv.date_invoice
                company_currency = inv.company_id.currency_id

                # create move lines (one per invoice line + eventual taxes and analytic lines)
                iml = inv.invoice_line_move_line_get()
                iml += inv.tax_line_move_line_get()

                diff_currency = inv.currency_id != company_currency
                # create one move line for the total and possibly adjust the other lines amount
                total, total_currency, iml = inv.with_context(ctx).compute_invoice_totals(company_currency, iml)
                name = inv.name or '/'
                if inv.payment_term_id:
                    totlines = \
                        inv.with_context(ctx).payment_term_id.with_context(currency_id=company_currency.id).compute(
                            total,
                            date_invoice)[
                            0]
                    res_amount_currency = total_currency
                    ctx['date'] = date_invoice
                    for i, t in enumerate(totlines):
                        if inv.currency_id != company_currency:
                            amount_currency = company_currency.with_context(ctx).compute(t[1], inv.currency_id)
                        else:
                            amount_currency = False

                        # last line: add the diff
                        res_amount_currency -= amount_currency or 0
                        if i + 1 == len(totlines):
                            amount_currency += res_amount_currency
                        if inv.manual_currency_rate_active:
                            iml.append({
                                'type': 'dest',
                                'name': name,
                                'price': price,
                                'account_id': inv.account_id.id,
                                'date_maturity': t[0],
                                'amount_currency': diff_currency and amount_currency,
                                'currency_id': diff_currency and inv.currency_id.id,
                                'invoice_id': inv.id
                            })
                        else:
                            iml.append({
                                'type': 'dest',
                                'name': name,
                                'price': t[1],
                                'account_id': inv.account_id.id,
                                'date_maturity': t[0],
                                'amount_currency': diff_currency and amount_currency,
                                'currency_id': diff_currency and inv.currency_id.id,
                                'invoice_id': inv.id
                            })
                else:
                    iml.append({
                        'type': 'dest',
                        'name': name,
                        'price': price if price else total,
                        'account_id': inv.account_id.id,
                        'date_maturity': inv.date_due,
                        'amount_currency': diff_currency and total_currency,
                        'currency_id': diff_currency and inv.currency_id.id,
                        'invoice_id': inv.id
                    })
                # if inv.manual_currency_rate_active:
                for i in iml:
                    rate = inv.manual_currency_rate if inv.manual_currency_rate_active else inv.currency_rate
                    price = i.get('amount_currency') * rate
                    if i.get('price') > 0 or i.get('type') == 'dest':
                        i.update({'price': price})
                    else:
                        i.update({'price': -price})
                part = self.env['res.partner']._find_accounting_partner(inv.partner_id)
                line = [(0, 0, self.line_get_convert(l, part.id)) for l in iml]
                line = inv.group_lines(iml, line)

                line = inv.finalize_invoice_move_lines(line)
                move_vals = {
                    'line_ids': line,
                }
                inv.move_id.write(move_vals)
                inv.move_id.post()
                # inv.write({'currency_rate': inv.manual_currency_rate})
        return res


    @api.one
    @api.depends('payment_move_line_ids.amount_residual')
    def _get_payment_info_JSON(self):
        self.payments_widget = json.dumps(False)
        super(account_invoice, self)._get_payment_info_JSON()
        current_info = json.loads(self.payments_widget)
        if self.payment_move_line_ids and self.manual_currency_rate_active:
            for payment in self.payment_move_line_ids:
                payment_currency_id = False
                if self.type in ('out_invoice', 'in_refund'):
                    amount = sum([p.amount for p in payment.matched_debit_ids if p.debit_move_id in self.move_id.line_ids])
                    amount_currency = sum(
                        [p.amount_currency for p in payment.matched_debit_ids if p.debit_move_id in self.move_id.line_ids])
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
                if payment_currency_id and payment_currency_id == self.currency_id:
                    amount_to_show = amount_currency
                elif self.manual_currency_rate:
                    amount_to_show = amount / self.manual_currency_rate
                else:
                    amount_to_show = payment.company_id.currency_id.with_context(date=payment.date).compute(amount,
                                                                                                            self.currency_id)
                if float_is_zero(amount_to_show, precision_rounding=self.currency_id.rounding):
                    continue
                payment_dict = filter(lambda info: info['payment_id'] == payment.id, current_info['content'])
                if payment_dict:
                    payment_dict[0].update(amount=amount_to_show)

            self.payments_widget = json.dumps(current_info)

    def _get_currency_rate(self):
        currency_rate = self.currency_rate
        if self.date and self.currency_id:
            currency_rate = self.env['res.currency.rate'].search([('name', '<=', self.date),
                                                                         ('currency_id', '=', self.currency_id.id)],
                                                                        limit=1, order='name desc').inverse_rate
        if self.manual_currency_rate_active and self.manual_currency_rate:
            currency_rate = self.manual_currency_rate
        return currency_rate


class AccountInvoiceRefund(models.TransientModel):
    """Refunds invoice"""
    _inherit = "account.invoice.refund"

    @api.multi
    def compute_refund(self, mode='refund'):
        context = dict(self._context or {})
        active_id = context.get('active_id', False)
        if active_id:
            inv = self.env['account.invoice'].browse(active_id)
        # res = super(AccountInvoiceRefund, self.with_context(
        #                       manual_currency_rate_active=inv.manual_currency_rate_active,
        #                       manual_currency_rate=inv.manual_currency_rate,
        #                       inv_id=inv.id,
        #                    )).compute_refund(mode=mode)
        res = super(AccountInvoiceRefund, self).compute_refund(mode=mode)
        refund_dom = res['domain']
        inv_ref = self.env['account.invoice'].search(refund_dom)
        inv_ref.write({'manual_currency_rate_active': inv.manual_currency_rate_active,
                       'manual_currency_rate': inv.manual_currency_rate})
        return res
