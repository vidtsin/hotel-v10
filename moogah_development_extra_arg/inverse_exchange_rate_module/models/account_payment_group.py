# -*- coding: utf-8 -*-
from __builtin__ import super
from collections import defaultdict
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError


class AccountPaymentGroup(models.Model):
    _inherit = 'account.payment.group'

    manual_currency_rate_active = fields.Boolean('Apply Manual Exchange', default=True)
    manual_currency_rate = fields.Float('Manual Rate', digits=(12, 6))
    tot_in_currency = fields.Monetary('To Pay - Payment Currency', currency_field='currency2_id',
                                      compute='_compute_tot_currency',
                                      help='Este campo muestra el total a pagar según la moneda y TC especificados en el encabezado del Pago/Recibo',
                                      )
    currency_rate = fields.Float('Today Exch. Rate', digits=(12, 6))
    currency2_id = fields.Many2one('res.currency', string="Payment Currency")
    currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id', readonly=True,
                                  translate=True)
    savedf = fields.Boolean()

    exchange_difference = fields.Monetary(string='Exchange  Differences', currency_field='currency_id',
                                          compute='_compute_exchange_differences')
    exchange_difference_aml_id = fields.Many2many('account.move.line', string="Exchange Difference line",
                                                  compute='_compute_exchange_difference_aml_id')

    inv_currency_id = fields.Many2one('res.currency', string="Invoice Currency", compute='_compute_total_inv_currency2')
    total_inv_currency2 = fields.Monetary(string='Total in Invoice Currency', compute='_compute_total_inv_currency2')

    tot_in_company_currency = fields.Monetary(string='To Pay – Company Currency', compute='_compute_tot_currency',
                                              currency_field='currency_id')

    to_pay_payment_currency = fields.Monetary(string='To Pay in Payment Currency ', compute='_compute_to_pay_currency',
                                              currency_field='currency2_id')
    to_pay_company_currency = fields.Monetary(string='To Pay in Company Currency ', compute='_compute_to_pay_currency',
                                              currency_field='currency_id')

    paid_payment_currency = fields.Monetary(string='Paid in Payment Currency ', compute='_compute_paid_currency',
                                            currency_field='currency2_id')
    paid_company_currency = fields.Monetary(string='Paid in Company Currency ', compute='_compute_paid_currency',
                                            currency_field='currency_id')

    prepayment_reference = fields.Char('Prepayment  Reference')

    unmatched_amount_payment_currency2 = fields.Monetary(currency_field='currency2_id',
                                                         compute="_compute_matched_amounts2",
                                                         string="Unmatched Amount Payment Currency")

    anticipate = fields.Boolean('Anticipate?', compute='_compute_anticipate', search="_search_anticipate")
    edit_reference = fields.Boolean('Edit Prepayment  Reference?', compute='_compute_edit_reference')
    show_message = fields.Boolean('Show message?', compute='_compute_show_message')
    edit_rate = fields.Boolean('Edit Rates?', compute='_compute_edit_rate')
    edit_billing_users = fields.Boolean('Edit billing user?', default=False)

    @api.model
    def default_get(self, fields):
        res = super(AccountPaymentGroup, self).default_get(fields)
        if 'currency_id' in res:
            res.update({'manual_currency_rate': 1, 'currency_rate': 1, 'currency2_id': res['currency_id']})
        return res

    @api.onchange('prepayment_reference')
    def onchange_prepayment_reference(self):
        if not self.edit_billing_users and self.prepayment_reference:
            self.edit_billing_users = (self.env.user.has_group(
                'account.group_account_invoice') or self.env.user.has_group(
                'account.group_account_user')) and not self.env.user.has_group('account.group_account_manager')

    @api.onchange('currency2_id')
    def onchange_currency_id(self):
        if self.currency2_id:
            currency = self.currency2_id.with_context(date=self.payment_date or fields.Date.context_today(self))
            currency_rate = currency.compute(1.0, self.company_id.currency_id)
            self.currency_rate = self._get_currency_rate(currency, currency_rate)
            self.manual_currency_rate = self.currency_rate

    @api.onchange('manual_currency_rate', 'to_pay_amount')
    def onchange_manual_currency_rate(self):
        if self.company_id.currency_id != self.currency2_id:
            self.tot_in_currency = self.to_pay_amount / self.manual_currency_rate

    @api.multi
    def check_currency_id(self):
        for rec in self:
            foundf = foundf2 = False
            cur_array = []

            cur_array.append(rec.currency2_id)
            if not rec.company_id.currency_id in cur_array:
                cur_array.append(rec.company_id.currency_id)
            if rec.currency2_id and not rec.currency2_id in cur_array:
                cur_array.append(rec.currency2_id)
            if rec.inv_currency_id and not rec.inv_currency_id in cur_array:
                cur_array.append(rec.inv_currency_id)
            if len(cur_array) > 2:
                raise UserError(_("El soporte para un 3er moneda en Pagos no está implementado. "
                                  "Por favor, realice transacciones considerando solo 2 monedas"))

    @api.model
    def create(self, vals):
        vals.update({'savedf': True})
        return super(AccountPaymentGroup, self).create(vals)

    @api.onchange('partner_id', 'partner_type', 'company_id')
    def _refresh_payments_and_move_lines(self):
        if self._context.get('pop_up'):
            return
        self.invalidate_cache(['payment_ids'])
        self.payment_ids.unlink()
        self.to_pay_move_line_ids -= self.to_pay_move_line_ids
        self.add_all()
        self._compute_to_pay_amount()

    @api.multi
    @api.depends('to_pay_move_line_ids', 'to_pay_move_line_ids.amount_residual_currency',
                 'to_pay_move_line_ids.amount_residual')
    def _compute_total_inv_currency2(self):
        for rec in self:
            currency = rec.to_pay_move_line_ids.mapped('invoice_id.currency_id') | rec.to_pay_move_line_ids.mapped(
                'currency_id')
            if currency:
                sign = rec.partner_type == 'supplier' and -1.0 or 1.0
                rec.inv_currency_id = currency[0].id
                if rec.inv_currency_id.id == rec.currency_id.id:
                    rec.total_inv_currency2 = sum(rec.to_pay_move_line_ids.mapped('amount_residual'))
                else:
                    rec.total_inv_currency2 = sum(rec.to_pay_move_line_ids.mapped('amount_residual_currency')) * sign

    @api.multi
    @api.depends('inv_currency_id', 'currency2_id', 'manual_currency_rate')
    def _compute_tot_currency(self):
        for rec in self:
            if rec.inv_currency_id.id == rec.currency2_id.id == rec.currency_id.id:
                rec.tot_in_currency = rec.selected_debt
                rec.tot_in_company_currency = rec.selected_debt
            if rec.inv_currency_id.id != rec.currency2_id.id == rec.currency_id.id:
                currency = self.currency2_id.with_context(date=rec.payment_date or fields.Date.context_today(rec))
                rec.tot_in_currency = rec.inv_currency_id.compute(rec.total_inv_currency2, currency)
                rec.tot_in_company_currency = rec.tot_in_currency
            if rec.inv_currency_id.id == rec.currency2_id.id != rec.currency_id.id:
                rec.tot_in_currency = rec.total_inv_currency2
                rec.tot_in_company_currency = rec.tot_in_currency * rec.manual_currency_rate
            if rec.inv_currency_id.id == rec.currency_id.id != rec.currency2_id.id:
                rec.tot_in_company_currency = rec.selected_debt
                if rec.manual_currency_rate:
                    rec.tot_in_currency = rec.tot_in_company_currency / rec.manual_currency_rate
                else:
                    rec.tot_in_currency = rec.tot_in_company_currency

    @api.multi
    @api.depends('currency2_id', 'payment_ids', 'manual_currency_rate', 'payment_ids.amount',
                 'payment_ids.currency_id', 'inv_currency_id')
    def _compute_to_pay_currency(self):
        for rec in self:
            rec.to_pay_payment_currency = sum(rec.payment_ids.mapped('pay_amount_currency2_id'))
            rec.to_pay_company_currency = rec.to_pay_payment_currency * rec.manual_currency_rate

    @api.multi
    @api.depends('currency2_id', 'payment_ids', 'manual_currency_rate', 'payment_ids.amount',
                 'payment_ids.currency_id', 'matched_move_line_ids')
    def _compute_paid_currency(self):
        for rec in self:
            rec.paid_company_currency = sum(rec.matched_move_line_ids.mapped(
                lambda m: m.with_context(payment_group_id=rec.id).payment_group_matched_amount))
            if rec.manual_currency_rate > 0:
                rec.paid_payment_currency = rec.paid_company_currency / rec.manual_currency_rate

    @api.multi
    @api.depends('state', 'matched_move_line_ids.payment_group_matched_amount', 'payments_amount', 'unmatched_amount')
    def _compute_matched_amounts2(self):
        for rec in self:
            if rec.manual_currency_rate > 0:
                rec.unmatched_amount_payment_currency2 = rec.unmatched_amount / rec.manual_currency_rate

    @api.multi
    @api.depends('unmatched_amount')
    def _compute_anticipate(self):
        for rec in self:
            rec.anticipate = rec.unmatched_amount > 0

    @api.multi
    @api.depends('edit_billing_users', 'selected_debt', 'payments_amount', 'state', 'prepayment_reference')
    def _compute_edit_reference(self):
        for rec in self:
            access_right = (self.env.user.has_group(
                'account.group_account_invoice') and not rec.edit_billing_users) or self.env.user.has_group(
                'account.group_account_manager')
            rec.edit_reference = access_right and ((rec.state == 'posted' and rec.anticipate) or (
                rec.state != 'posted' and rec.selected_debt < rec.payments_amount))
            rec.show_message = rec.state == 'posted' and rec.anticipate and not rec.prepayment_reference

    @api.multi
    def _compute_show_message(self):
        for rec in self:
            rec.show_message = rec.state == 'posted' and rec.anticipate and not rec.prepayment_reference

    @api.multi
    @api.depends('payment_ids')
    def _compute_edit_rate(self):
        for rec in self:
            rec.edit_rate = not rec.payment_ids

    @api.multi
    def _search_anticipate(self, operator, value):
        rec_ids = []
        if value is True and operator == '=':
            recs = self.search([('state', '=', 'posted')])
            rec_ids = recs.filtered(lambda p: p.unmatched_amount).ids
        return [('id', 'in', rec_ids)]

    @api.multi
    @api.depends('payment_ids.state', 'payment_ids')
    def _compute_exchange_difference_aml_id(self):
        for rec in self:
            aml = self.env['account.move.line'].search([('move_id.document_number', '=', rec.display_name),
                                                        ('journal_id', '=',
                                                         rec.company_id.currency_exchange_journal_id.id),
                                                        ('account_id.internal_type', 'in', ('receivable', 'payable'))])
            rec.exchange_difference_aml_id = aml and aml.ids

    @api.multi
    @api.depends('currency2_id', 'inv_currency_id', 'manual_currency_rate', 'payment_ids', 'payment_ids.amount',
                 'payment_ids.state')
    def _compute_exchange_differences(self):
        for rec in self:
            exchange_difference = 0
            if rec.exchange_difference_aml_id:
                exchange_difference = reduce(lambda x, y: x - y,
                                             rec.exchange_difference_aml_id.mapped(lambda p: p.credit or p.debit))
            rec.exchange_difference = exchange_difference

    @api.one
    def _get_exchange_differences(self, residual_list, invoices=True, anticipe=True):
        exchange_difference = 0
        if self.inv_currency_id.id == self.currency2_id.id != self.currency_id.id:
            total_inv_company_currency = sum(self.to_pay_move_line_ids.mapped(lambda p: abs(p.balance)))
            total_paid_company_currency = sum(self.to_pay_move_line_ids.mapped(
                lambda p: abs(p.with_context(payment_group_id=self.id).payment_group_matched_amount)))
            partial = False
            if total_inv_company_currency > total_paid_company_currency:
                partial = True
            inv_lines = pay_lines = self.env['account.move.line']
            for line_to_pay in self.to_pay_move_line_ids:  # .filtered(lambda l: l.id in ids_list)
                inv = invoices and line_to_pay.mapped('invoice_id')
                pay = anticipe and line_to_pay.mapped('payment_id')
                paid_amount = line_to_pay.with_context(payment_group_id=self.id).payment_group_matched_amount
                if inv or pay:
                    origin = inv or pay.payment_group_id or pay
                    org_rate = origin.manual_currency_rate_active and origin.manual_currency_rate or origin.currency_rate
                    if residual_list and filter(lambda x: x.get(line_to_pay.id), residual_list):
                        paid_amount_2 = filter(lambda x: x.get(line_to_pay.id), residual_list)[0].get(
                            line_to_pay.id) - (self.partner_type == 'supplier' and abs(
                            line_to_pay.amount_residual_currency) or line_to_pay.amount_residual_currency)
                    else:
                        paid_amount_2 = partial and self.manual_currency_rate and paid_amount / self.manual_currency_rate or org_rate and paid_amount / org_rate
                    exchange_difference += paid_amount_2 * abs(self.manual_currency_rate - org_rate)
                if inv:
                    inv_lines += line_to_pay
                if pay:
                    pay_lines += line_to_pay

        return exchange_difference, inv_lines, pay_lines

    @api.constrains('to_pay_move_line_ids', 'debt_move_line_ids')
    def _check_move_line_currency(self):
        for group in self:
            if self.env.context.get('check_currency', True):
                currencies = group.to_pay_move_line_ids.mapped('invoice_id.currency_id')
                currencies |= group.to_pay_move_line_ids.mapped('currency_id')
                if len(currencies) > 1:
                    raise ValidationError(
                        _('Payments/Receipts with invoices in more than one currency are not allowed'))
        return True

    @api.multi
    def _check_payment_ids_currency(self):
        for group in self:
            currencies = group.payment_ids.mapped('currency_id')
            if len(currencies) > 2:
                raise ValidationError(_('More than two currencies are not allowed on payments lines'))
            if group.payment_ids.filtered(
                    lambda p: p.currency_id.id == group.currency2_id.id
                    and p.manual_currency_rate != group.manual_currency_rate):
                raise ValidationError(
                    _('Payment lines must use the same currency rate defined on payment group'))
        return True

    @api.multi
    def _check_payment_inv_currency(self):
        for group in self:
            currencies = group.payment_ids.mapped('currency_id')
            if group.inv_currency_id and currencies:
                if group.inv_currency_id.id not in currencies.ids:
                    raise ValidationError(_('Invoices currency is not among the payments currency'))
        return True

    @api.multi
    def _create_exchange_rate_entry(self, aml_to_fix, amount_diff, diff_in_currency, currency, move_date):
        for rec in self:
            if not rec.company_id.currency_exchange_journal_id:
                raise UserError(_(
                    "You should configure the 'Exchange Rate Journal' in the accounting settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))
            if not rec.company_id.income_currency_exchange_account_id.id:
                raise UserError(_(
                    "You should configure the 'Gain Exchange Rate Account' in the accounting settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))
            if not rec.company_id.expense_currency_exchange_account_id.id:
                raise UserError(_(
                    "You should configure the 'Loss Exchange Rate Account' in the accounting settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))
            move_vals = {'journal_id': rec.company_id.currency_exchange_journal_id.id,
                         'document_type_id': rec.receiptbook_id.document_type_id.id,
                         'document_number': rec.display_name
                         }
            if move_date > rec.company_id.fiscalyear_lock_date:
                move_vals['date'] = move_date
            move = rec.env['account.move'].create(move_vals)
            amount_diff = rec.company_id.currency_id.round(amount_diff)
            diff_in_currency = currency.round(diff_in_currency)
            line_to_reconcile = rec.env['account.move.line'].with_context(check_move_validity=False).create({
                'name': _('Currency exchange rate difference'),
                'debit': amount_diff < 0 and -amount_diff or 0.0,
                'credit': amount_diff > 0 and amount_diff or 0.0,
                'account_id': rec.payment_ids.mapped('destination_account_id')[0].id,
                'move_id': move.id,
                'currency_id': currency.id,
                'amount_currency': -diff_in_currency,
                'partner_id': rec.partner_id.id,
            })
            rec.env['account.move.line'].create({
                'name': _('Currency exchange rate difference'),
                'debit': amount_diff > 0 and amount_diff or 0.0,
                'credit': amount_diff < 0 and -amount_diff or 0.0,
                'account_id': amount_diff > 0 and rec.company_id.currency_exchange_journal_id.default_debit_account_id.id or rec.company_id.currency_exchange_journal_id.default_credit_account_id.id,
                'move_id': move.id,
                'currency_id': currency.id,
                'amount_currency': diff_in_currency,
                'partner_id': rec.partner_id.id,
            })
            # for aml in aml_to_fix:
            #     partial_rec = rec.env['account.partial.reconcile'].create({
            #         'debit_move_id': aml.credit and line_to_reconcile.id or aml.id,
            #         'credit_move_id': aml.debit and line_to_reconcile.id or aml.id,
            #         'amount': abs(aml.amount_residual),
            #         'amount_currency': abs(aml.amount_residual_currency),
            #         'currency_id': currency.id,
            #     })
            move.post()
            return line_to_reconcile

    @api.multi
    def _check_difference_exchange_rate(self, current_inv_residual):
        for rec in self:
            current_residual = current_inv_residual.get(rec.id)
            native_exchange_moves = rec.matched_move_line_ids.filtered(lambda line: not line.move_id.document_type_id
                                                                                    and line.journal_id.id == rec.company_id.currency_exchange_journal_id.id).mapped(
                'move_id')
            if not native_exchange_moves:
                native_exchange_moves = self.env['account.move'].search(
                    [('document_type_id', '=', rec.receiptbook_id.document_type_id.id),
                     ('document_number', '=', rec.id)])

            # ********************
            exch_lines = self.env['account.move.line']
            pay_reconcile = rec.mapped('payment_ids').mapped('move_line_ids').filtered(
                lambda p: p.account_id.reconcile)
            # *******************
            if native_exchange_moves:
                native_exchange_moves.write({'document_number': rec.display_name,
                                             'document_type_id': rec.receiptbook_id.document_type_id.id})
                exch_lines += native_exchange_moves.mapped('line_ids').filtered(lambda p: p.account_id.reconcile)
            else:
                difference1 = rec._get_exchange_differences(current_residual, True, False)[0]
                difference2 = rec._get_exchange_differences(current_residual, False, True)[0]
                aml_to_fix = not rec.unmatched_amount and pay_reconcile or []
                for difference in [difference1, difference2]:
                    if difference[0]:
                        sign = rec.partner_type == 'supplier' and not difference[2] and 1.0 or -1.0
                        exchange_difference = difference[0] * sign
                        inv_reconcile = rec.to_pay_move_line_ids.filtered(
                            lambda l: l.invoice_id.id and l.account_id.reconcile)
                        exch_reconcile = rec._create_exchange_rate_entry(aml_to_fix, exchange_difference,
                                                                         0, rec.currency2_id,
                                                                         rec.payment_date)
                        exch_lines += exch_reconcile
                if not aml_to_fix:
                    (pay_reconcile + exch_lines).auto_reconcile_lines()
            if exch_lines:
                (pay_reconcile + rec.to_pay_move_line_ids + exch_lines).auto_reconcile_lines()

    @api.multi
    def post(self):
        self.check_currency_id()
        self._check_payment_ids_currency()
        current_inv_residual = defaultdict(list)
        for rec in self:
            residual = rec.to_pay_move_line_ids.mapped(lambda p: {
                p.id: rec.partner_type == 'supplier' and abs(p.amount_residual_currency) or p.amount_residual_currency})
            current_inv_residual[rec.id].extend([x for x in residual])
            exchanges_entries = self.search(
                [('partner_id', '=', rec.partner_id.id), ('state', '=', 'posted'),
                 ('to_pay_move_line_ids', 'in', rec.to_pay_move_line_ids.ids)]).filtered(
                lambda p: p.exchange_difference_aml_id).mapped('exchange_difference_aml_id').filtered(
                lambda m: not m.reconciled)
            rec.to_pay_move_line_ids = exchanges_entries | rec.to_pay_move_line_ids
            super(AccountPaymentGroup, rec).post()
            if rec.currency2_id.id == rec.inv_currency_id.id != rec.currency_id.id:
                rec._check_difference_exchange_rate(current_inv_residual)

    def _get_currency_rate(self, currency, rate):
        if self.payment_date:
            currency_rate = self.env['res.currency.rate'].search([('name', '<=', self.payment_date),
                                                                         ('currency_id', '=', currency.id)],
                                                                        limit=1, order='name desc').inverse_rate
        return currency_rate and currency_rate or rate

    _sql_constraints = [
        ('positive_rate', 'CHECK(manual_currency_rate >= 0)', _('The Manual Rate can not be negative'))
    ]
