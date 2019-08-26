# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.model
    def compute_amount_fields_custom(self, obj, amount, src_currency, company_currency, invoice_currency=False,
                                     currency_rate=False):
        """ Helper function to compute value for fields debit/credit/amount_currency based on an amount and the currencies given in parameter"""
        amount_currency = False
        currency_id = False
        if src_currency and src_currency != company_currency:
            amount_currency = amount
            amount = amount_currency * obj.manual_currency_rate
            currency_id = src_currency.id
        debit = amount > 0 and amount or 0.0
        credit = amount < 0 and -amount or 0.0
        if invoice_currency and invoice_currency != company_currency and not amount_currency:
            amount_currency = amount * obj.manual_currency_rate
            currency_id = invoice_currency.id
            if currency_rate:
                amount_currency = amount / currency_rate
        return debit, credit, amount_currency, currency_id


class AccountAbstractPayment(models.AbstractModel):
    _inherit = "account.abstract.payment"

    def _compute_total_invoices_amount(self):
        """ Compute the sum of the residual of invoices, expressed in the payment currency """
        payment_currency = self.currency_id or self.journal_id.currency_id or self.journal_id.company_id.currency_id
        invoices = self._get_invoices()
        if all(inv.currency_id == payment_currency for inv in invoices):
            total = sum(invoices.mapped('residual_signed'))
        else:
            if not self.manual_currency_rate_active:
                total = 0
                for inv in invoices:
                    if inv.company_currency_id != payment_currency:
                        total += inv.company_currency_id.with_context(date=self.payment_date).compute(
                            inv.residual_company_signed, payment_currency)
                    else:
                        total += inv.residual_company_signed
            else:
                total = 0
                for inv in invoices:
                    total += inv.residual / self.manual_currency_rate
        return abs(total)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    manual_currency_rate_active = fields.Boolean('Apply Manual Exchange', readonly=True, default=True)
    manual_currency_rate = fields.Float('Inverse Rate', digits=(12, 6), compute='_compute_manual_currency_rate',
                                        store=True)
    currency2_id = fields.Many2one('res.currency', related='payment_group_id.currency2_id', string="Payment Currency")
    company_currency_id = fields.Many2one('res.currency', related='payment_group_id.currency_id',
                                          string="Company Currency")
    pay_amount_currency2_id = fields.Monetary(string='Payment Amount in Payment Currency',
                                              compute='_compute_pay_amount_currency2_id', currency_field='currency2_id')

    currency_rate = fields.Float('Currency Rate', readonly=True, related='payment_group_id.manual_currency_rate',
                                 digits=(12, 6))
    to_pay_payment_currency = fields.Monetary(string='To Pay in Payment Currency',
                                              compute='_compute_to_pay_currency',
                                              currency_field='currency2_id')
    to_pay_company_currency = fields.Monetary(string='To Pay in Company Currency',
                                              compute='_compute_to_pay_currency',
                                              currency_field='company_currency_id')

    @api.multi
    @api.depends('pay_amount_currency2_id', 'amount', 'currency_id', 'readonly_amount2')
    def _compute_to_pay_currency(self):
        for rec in self:
            total = sum(rec.payment_group_id.mapped('payment_ids').mapped('pay_amount_currency2_id'))
            rec.to_pay_payment_currency = total
            rec.to_pay_company_currency = rec.to_pay_payment_currency * rec.currency_rate

    @api.multi
    @api.depends('currency_id')
    def _compute_manual_currency_rate(self):
        for rec in self:
            if rec.currency_id and rec.currency_id != rec.currency2_id:
                rec.manual_currency_rate = rec.currency_id.rate
            else:
                rec.manual_currency_rate = rec.currency_rate

    @api.multi
    @api.depends('currency_id', 'amount', 'readonly_amount2')
    def _compute_pay_amount_currency2_id(self):
        for rec in self:
            if rec.readonly_amount2 and rec.readonly_amount2 == rec.amount and rec.currency_id.id == rec.currency2_id.id:
                rec.pay_amount_currency2_id = rec.amount / rec.currency_rate
            elif rec.currency_id.id == rec.currency2_id.id:
                rec.pay_amount_currency2_id = rec.amount
            elif rec.currency_id.id == rec.company_currency_id.id and rec.currency_rate:
                rec.pay_amount_currency2_id = rec.amount / rec.currency_rate
            else:
                currency = rec.currency2_id.with_context(date=rec.payment_date or fields.Date.context_today(rec))
                rec.pay_amount_currency2_id = rec.currency_id.compute(rec.amount, currency)

    @api.one
    @api.depends('amount', 'currency_id', 'company_id.currency_id')
    def _compute_amount_company_currency(self):
        payment_currency = self.currency_id
        company_currency = self.company_id.currency_id
        if self.payment_group_id and payment_currency == self.payment_group_id.currency2_id and self.manual_currency_rate_active:
            amount_company_currency = self.amount * self.manual_currency_rate
        elif payment_currency and payment_currency != company_currency:
            amount_company_currency = self.currency_id.with_context(
                date=self.payment_date).compute(
                self.amount, self.company_id.currency_id)
        else:
            amount_company_currency = self.amount
        sign = 1.0
        if (
                    (self.partner_type == 'supplier' and
                                 self.payment_type == self.payment_type == 'inbound') or
                    (self.partner_type == 'customer' and
                                 self.payment_type == self.payment_type == 'outbound')):
            sign = -1.0
        self.amount_company_currency = amount_company_currency * sign

    @api.one
    @api.depends('invoice_ids', 'amount', 'payment_date', 'currency_id', 'manual_currency_rate')
    def _compute_payment_difference(self):
        if len(self.invoice_ids) == 0:
            return
        if self.invoice_ids[0].type in ['in_invoice', 'out_refund']:
            self.payment_difference = self.amount - self._compute_total_invoices_amount()
        else:
            self.payment_difference = self._compute_total_invoices_amount() - self.amount

    def _create_payment_entry(self, amount):
        """ Create a journal entry corresponding to a payment, if the payment references invoice(s) they are reconciled.
            Return the journal entry.
        """
        aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
        invoice_currency = False
        currency_rate = counterpart_currency_id = False
        if self.invoice_ids and all([x.currency_id == self.invoice_ids[0].currency_id for x in self.invoice_ids]):
            # if all the invoices selected share the same currency, record the paiement in that currency too
            invoice_currency = self.invoice_ids[0].currency_id
        if self.manual_currency_rate_active:
            if self.currency_id == self.company_id.currency_id != self.currency2_id:
                if self.payment_group_id and self.payment_group_id.inv_currency_id:
                    currency_rate = self.currency_rate
                    invoice_currency = self.payment_group_id.inv_currency_id

            debit, credit, amount_currency, currency_id = aml_obj.with_context(
                date=self.payment_date).compute_amount_fields_custom(self, amount, self.currency_id,
                                                                     self.company_id.currency_id, invoice_currency,
                                                                     currency_rate)
            counterpart_currency_id = currency_id
        else:
            debit, credit, amount_currency, currency_id = aml_obj.with_context(
                date=self.payment_date).compute_amount_fields(amount, self.currency_id, self.company_id.currency_id,
                                                              invoice_currency)
        move = self.env['account.move'].create(self._get_move_vals())

        # Write line corresponding to invoice payment
        counterpart_aml_dict = self._get_shared_move_line_vals(debit, credit, amount_currency, move.id, False)
        counterpart_aml_dict.update(self._get_counterpart_move_line_vals(self.invoice_ids))
        counterpart_aml_dict.update({'currency_id': currency_id})
        counterpart_aml = aml_obj.create(counterpart_aml_dict)
        # Reconcile with the invoices
        if self.payment_difference_handling == 'reconcile' and self.payment_difference:
            writeoff_line = self._get_shared_move_line_vals(0, 0, 0, move.id, False)
            amount_currency_wo, currency_id = aml_obj.with_context(date=self.payment_date).compute_amount_fields(
                self.payment_difference, self.currency_id, self.company_id.currency_id, invoice_currency)[2:]
            # the writeoff debit and credit must be computed from the invoice residual in company currency
            # minus the payment amount in company currency, and not from the payment difference in the payment currency
            # to avoid loss of precision during the currency rate computations. See revision 20935462a0cabeb45480ce70114ff2f4e91eaf79 for a detailed example.
            total_residual_company_signed = sum(invoice.residual_company_signed for invoice in self.invoice_ids)
            total_payment_company_signed = self.currency_id.with_context(date=self.payment_date).compute(self.amount,
                                                                                                         self.company_id.currency_id)
            if self.invoice_ids[0].type in ['in_invoice', 'out_refund']:
                amount_wo = total_payment_company_signed - total_residual_company_signed
            else:
                amount_wo = total_residual_company_signed - total_payment_company_signed
            debit_wo = amount_wo > 0 and amount_wo or 0.0
            credit_wo = amount_wo < 0 and -amount_wo or 0.0
            writeoff_line['name'] = _('Counterpart')
            writeoff_line['account_id'] = self.writeoff_account_id.id
            writeoff_line['debit'] = debit_wo
            writeoff_line['credit'] = credit_wo
            writeoff_line['amount_currency'] = amount_currency_wo
            writeoff_line['currency_id'] = currency_id
            writeoff_line = aml_obj.create(writeoff_line)
            if counterpart_aml['debit']:
                counterpart_aml['debit'] += credit_wo - debit_wo
            if counterpart_aml['credit']:
                counterpart_aml['credit'] += debit_wo - credit_wo
            counterpart_aml['amount_currency'] -= amount_currency_wo
        self.invoice_ids.register_payment(counterpart_aml)

        # Write counterpart lines
        if not self.currency_id != self.company_id.currency_id and not currency_rate:#
            amount_currency = 0
        liquidity_aml_dict = self._get_shared_move_line_vals(credit, debit, -amount_currency, move.id, False)
        liquidity_aml_dict.update(self._get_liquidity_move_line_vals(-amount))
        if currency_rate and counterpart_currency_id:
            liquidity_aml_dict.update({'currency_id': currency_id})
        aml_obj.create(liquidity_aml_dict)

        move.post()
        return move

#
