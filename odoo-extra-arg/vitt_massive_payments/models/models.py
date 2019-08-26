# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import ValidationError

MAP_INVOICE_TYPE_PARTNER_TYPE = {
    'out_invoice': 'customer',
    'out_refund': 'customer',
    'in_invoice': 'supplier',
    'in_refund': 'supplier',
}

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    reversed = fields.Boolean(string="Reversed",readonly=True)

# class AccountJournal(models.Model):
#     _inherit = 'account.journal'
#
#     def _get_manual_mp(self):
#         m_id = self.env.ref("account.account_payment_method_manual_out")
#         if self.outbound_payment_method_ids._ids == m_id.id:
#             return True
#         return False
#     only_manual = fields.Boolean(compute="_get_manual_mp")

class AccountPaymentType(models.Model):
    _name = 'account.payment.type'

    name = fields.Char(string="payment Type")


class MassivePayemntInvoice(models.Model):
    _name = 'massive.payment.invoices'
    _order = "partner_id asc"

    payment_header_id = fields.Many2one('massive.payment')
    partner_id = fields.Many2one(related="invoice_id.partner_id",string="Client",translate=True,readonly=True,index=True)
    invoice_id = fields.Many2one('account.invoice',string="Invoice",translate=True,index=True,
                                 domain="[('type', '=', 'in_invoice'),('state', '=', 'open')]")
    date = fields.Date(related="invoice_id.date_invoice",string="Date",translate=True,readonly=True)
    residual = fields.Float(string="Residual",translate=True)
    payment_amount = fields.Float(string="Payment Amount",translate=True)
    payment_id = fields.Many2one('account.payment',string="Payment Nr",translate=True,readonly=True)
    partner_name = fields.Char(related="partner_id.name")
    date_due =fields.Date(related="invoice_id.date_due",string="Due Date",translate=True)

    @api.onchange('invoice_id','residual')
    def onchange_invoice_id(self):
        self.residual = self.invoice_id.residual


class MassivePayment(models.Model):
    _name = 'massive.payment'

    name = fields.Char(string='Name', size=64, readonly=True, default='/',translate=True)
    journal_id = fields.Many2one('account.journal',
                                 string='Journal',
                                 translate=True,
                                 domain="[('type', 'in', ['bank','cash']),('outbound_payment_method_ids', '!=', False)]",
                                 required=True)
    payment_date = fields.Date(string='Date', required=True,default=datetime.now().strftime('%Y-%m-%d'),translate=True)
    use_invoice_date = fields.Boolean(string="Use Invoice Date",translate=True)
    payment_type = fields.Many2one('account.payment.type',string="Payment Type",translate=True)
    reference = fields.Char(string="Reference",translate=True)
    invoice_ids = fields.One2many('massive.payment.invoices','payment_header_id')
    notes = fields.Text(string="Notes",translate=True)
    approved_id = fields.Many2one('res.users',string="Approved By",translate=True,readonly=True)
    approved_date = fields.Datetime(string="Approved Date",translate=True,readonly=True)
    confirmed_id = fields.Many2one('res.users',string="Confirmed By",translate=True,readonly=True)
    confirmed_date = fields.Datetime(string="Confirmed Date",translate=True,readonly=True)
    canceled_id = fields.Many2one('res.users',string="Canceled By",translate=True,readonly=True)
    canceled_date = fields.Datetime(string="Canceled Date",translate=True,readonly=True)
    state = fields.Selection([('draft', 'Draft'),('confirmed', 'Confirmed'),('done', 'Done'),('cancel', 'Canceled')],translate=True)
    total_amount = fields.Monetary(string="Total Amount",translate=True)
    company_id = fields.Many2one('res.company',readonly=True)
    currency_id = fields.Many2one('res.currency',readonly=True)

    @api.multi
    @api.onchange('invoice_ids','invoice_ids.residual','invoice_ids.invoice_id','invoice_ids.payment_amount')
    @api.depends('invoice_ids','invoice_ids.residual','invoice_ids.invoice_id','invoice_ids.payment_amount')
    def _get_total_amount(self):
        self.ensure_one()
        self.total_amount = 0
        if self.invoice_ids:
            for inv in self.invoice_ids:
                self.total_amount += inv.payment_amount

    @api.constrains('invoice_ids')
    def constrains_same_invoice(self):
        ids = list()
        if self.invoice_ids:
            for inv in self.invoice_ids:
                if inv.invoice_id.id in ids:
                    raise ValidationError(_("you Can't enter the same Invoice twice %s" % inv.invoice_id.display_name))
                ids.append(inv.invoice_id.id)


    @api.model
    def default_get(self,fields):
        res = super(MassivePayment, self).default_get(fields)
        res['currency_id'] = self.env['res.company']._company_default_get('vitt_massive_payments').currency_id.id
        res['company_id'] = self.env['res.company']._company_default_get('vitt_massive_payments').id
        res['state'] = 'draft'
        return res

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('massive.payments')
        res = super(MassivePayment, self).create(vals)
        return res


    def confirm_paym(self):
        self.write({'state':'confirmed','confirmed_id':self.env.user.id,'confirmed_date':fields.Datetime.now()})

    def unconfirm_paym(self):
        self.write({'state':'draft'})

    def draft_paym(self):
        self.write({'state':'draft'})

    def validate_paym(self):
        for invoice in self.invoice_ids:
            rec = dict()
            paym = self.env['account.payment']
            if self.reference:
                rec['communication'] = self.reference
            else:
                rec['communication'] = invoice.invoice_id.reference or invoice.invoice_id.name or invoice.invoice_id.number
            rec['currency_id'] = invoice.invoice_id.currency_id.id
            rec['payment_type'] = invoice.invoice_id.type in ('out_invoice', 'in_refund') and 'inbound' or 'outbound'
            rec['partner_type'] = MAP_INVOICE_TYPE_PARTNER_TYPE[invoice.invoice_id.type]
            rec['partner_id'] = invoice.invoice_id.partner_id.id
            rec['amount'] = invoice.payment_amount
            rec['invoice_ids'] = [(6, 0, [invoice.invoice_id.id])]
            rec['journal_id'] = self.journal_id.id
            rec['payment_method_id'] = self.journal_id.outbound_payment_method_ids[0].id
            if self.use_invoice_date:
                rec['payment_date'] = invoice.invoice_id.date_invoice
            else:
                rec['payment_date'] = self.payment_date

            paym = paym.create(rec)
            paym.post()
            invoice.write({'payment_id':paym.id})
        self.write({'state':'done','approved_id':self.env.user.id,'approved_date':fields.Datetime.now()})

    def cancel_paym(self):
        for invoice in self.invoice_ids:
            if invoice.payment_id:
                invoice.payment_id.cancel()
                invoice.payment_id.write({'move_name':""})
                invoice.payment_id.unlink()
                invoice.write({'payment_id': False})
            # if invoice.payment_id.move_line_ids:
            #     move = invoice.payment_id.move_line_ids[0].move_id
            #     if self.use_invoice_date:
            #         move.reverse_moves(invoice.invoice_id.date_invoice, invoice.payment_id.journal_id or False)
            #     else:
            #         move.reverse_moves(self.payment_date, invoice.payment_id.journal_id or False)
            #     invoice.payment_id.write({'reversed':True})
        self.write({'state':'cancel','canceled_id':self.env.user.id,'canceled_date':fields.Datetime.now()})


class AccountPaymentWizard(models.TransientModel):
    _name = 'account.payment.wizard'

    journal_id = fields.Many2one('account.journal',
                                 string='Journal',
                                 translate=True,
                                 domain="[('type', 'in', ['bank','cash']),('outbound_payment_method_ids', '!=', False)]",
                                 required=True)
    payment_date = fields.Date(string='Date', required=True,default=datetime.now().strftime('%Y-%m-%d'),translate=True)

    def Procced(self):
        if not self.journal_id or not self.payment_date:
            raise ValidationError(_("Please fill mandatory Fields"))

        active_ids = self.env.context.get('active_ids', [])
        invoices = self.env['account.invoice'].browse(active_ids)
        for inv in invoices:
            if inv.currency_id != self.env['res.company']._company_default_get('vitt_massive_payments').currency_id:
                raise ValidationError(_("invoices in the company currency ONLY"))
            if inv.type not in ['in_invoice','in_refund']:
                raise ValidationError(_("for Purchase Invoices ONLY"))
            if inv.type not in ['in_invoice']:
                raise ValidationError(_("Credit Notes not allowed %s" % inv.display_name))

        mp = self.env['massive.payment'].create({'journal_id':self.journal_id.id,'payment_date':self.payment_date})
        mpi = self.env['massive.payment.invoices']
        for inv in invoices:
            mpi.create({'payment_header_id':mp.id,'invoice_id':inv.id,'residual':inv.residual,'payment_amount':inv.residual})
        mp._get_total_amount()
        return {
            'view_mode': 'form',
            'res_id': mp.id,
            'res_model': 'massive.payment',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
        }

