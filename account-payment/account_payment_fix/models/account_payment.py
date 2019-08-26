# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # nuevo campo funcion para definir dominio de los metodos
    payment_method_ids = fields.Many2many(
        'account.payment.method',
        compute='_compute_payment_methods'
    )
    journal_ids = fields.Many2many(
        'account.journal',
        compute='_compute_journals'
    )
    # journal_at_least_type = fields.Char(
    #     compute='_compute_journal_at_least_type'
    # )
    destination_journal_ids = fields.Many2many(
        'account.journal',
        compute='_compute_destination_journals'
    )
    inbound = fields.Boolean()  #domain
    outbound = fields.Boolean() #domain
    readonly_amount2 = fields.Monetary(string='Monto a Pagar',readonly=True,translate=True)

    @api.onchange('payment_method_id','journal_id')
    def _onchange_payment_method_id2(self):
        self.hide_payment_method = True

    @api.onchange('journal_id')
    def _onchange_journal_id2(self):
        if self.journal_id.id:
            domain = [
                ('type', 'in', ('bank', 'cash')),
                ('inbound_payment_method_ids', 'in', self.journal_id.inbound_payment_method_ids.filtered(
                    lambda x: x.code not in ['received_third_check', 'delivered_third_check', 'issue_check']).ids),
                ('outbound_payment_method_ids', 'in', self.journal_id.outbound_payment_method_ids.filtered(
                    lambda x: x.code not in ['received_third_check', 'delivered_third_check', 'issue_check']).ids),
                ('company_id', '=', self.journal_id.company_id.id),
            ]
            return {'domain': {'destination_journal_id': domain}}


    @api.multi
    @api.depends('journal_id')
    def _compute_destination_journals(self):
        for rec in self:
            domain = [
                ('type', 'in', ('bank', 'cash')),
                ('at_least_one_inbound', '=', True),
                ('company_id', '=', rec.journal_id.company_id.id),
            ]
            rec.destination_journal_ids = rec.journal_ids.search(domain)

    @api.multi
    def get_journals_domain(self):
        """
        We get domain here so it can be inherited
        """
        self.ensure_one()
        domain = [('type', 'in', ('bank', 'cash'))]
        if self.payment_type == 'inbound':
            domain.append(('at_least_one_inbound', '=', True))
        else:
            domain.append(('at_least_one_outbound', '=', True))
        return domain

    @api.multi
    @api.depends('payment_type')
    def _compute_journals(self):
        for rec in self:
            rec.journal_ids = rec.journal_ids.search(rec.get_journals_domain())

    @api.multi
    @api.depends(
        'journal_id.outbound_payment_method_ids',
        'journal_id.inbound_payment_method_ids',
        'payment_type',
    )
    def _compute_payment_methods(self):
        for rec in self:
            if rec.payment_type in ('outbound', 'transfer'):
                methods = self.journal_id.outbound_payment_method_ids
            else:
                methods = self.journal_id.inbound_payment_method_ids
            rec.payment_method_ids = methods

    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        """
        Sobre escribimos y desactivamos la parte del dominio de la funcion
        original ya que se pierde si se vuelve a entrar
        """
        if not self.invoice_ids:
            # Set default partner type for the payment type
            if self.payment_type == 'inbound':
                self.partner_type = 'customer'
            elif self.payment_type == 'outbound':
                self.partner_type = 'supplier'

    # @api.onchange('partner_type')
    def _onchange_partner_type(self):
        """
        Agregasmos dominio en vista ya que se pierde si se vuelve a entrar
        Anulamos funcion original porque no haria falta
        """
        return True

    @api.onchange('journal_id')
    def _onchange_journal(self):
        """
        Sobre escribimos y desactivamos la parte del dominio de la funcion
        original ya que se pierde si se vuelve a entrar
        """
        if self.journal_id:
            self.currency_id = (
                self.journal_id.currency_id or self.company_id.currency_id)
            # Set default payment method
            # (we consider the first to be the default one)
            payment_methods = (
                self.payment_type == 'inbound' and
                self.journal_id.inbound_payment_method_ids or
                self.journal_id.outbound_payment_method_ids)
            self.payment_method_id = (
                payment_methods and payment_methods[0] or False)

    @api.constrains('vendorbill','customerbill','payment_type','payment_method_code')
    def constrains_vendor_customer_bill(self):
        if self.payment_method_code == 'withholding':
            if self.payment_type == 'inbound' and self.vendorbill:
                raise ValidationError(_('en la linea del pago afectada a retencion no puede tener una factura de proveedor'))
            if self.payment_type == 'inbound' and not self.customerbill:
                raise ValidationError(_('en la linea del pago afectada a retencion debe tener una factura de cliente'))
            if self.payment_type == 'outbound' and not self.vendorbill:
                raise ValidationError(_('en la linea del recibo afectada a retencion debe tener una factura de proveedor'))
            if self.payment_type == 'outbound' and self.customerbill:
                raise ValidationError(_('en la linea del recibo afectada a retencion no puede tener una factura de cliente'))


    @api.one
    @api.depends('invoice_ids', 'payment_type', 'partner_type', 'partner_id')
    def _compute_destination_account_id(self):
        """
        We send force_company on context so payments can be created from parent
        companies. We try to send force_company on self but it doesnt works, it
        only works sending it on partner
        """
        res = super(AccountPayment, self)._compute_destination_account_id()
        if not self.invoice_ids and self.payment_type != 'transfer':
            partner = self.partner_id.with_context(
                force_company=self.company_id.id)
            if self.partner_type == 'customer':
                self.destination_account_id = (
                    partner.property_account_receivable_id.id)
            else:
                self.destination_account_id = (
                    partner.property_account_payable_id.id)
        return res

    @api.model
    def default_get(self, fields):
        res = super(AccountPayment, self).default_get(fields)
        if 'payment_type' in res:
            if res['payment_type'] == 'inbound':
                res.update({'inbound':True})
            else:
                res.update({'outbound':True})
        res.update({'hide_payment_method':True})
        if 'amount' in res:
            res.update({'readonly_amount2':res['amount']})

        return res