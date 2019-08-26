# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    obj_bool = fields.Boolean(string="Objected",translate=True,index=True)
    obj_value = fields.Float(string="Objected Value",translate=True)

    @api.onchange('obj_bool')
    def obj_bool_onchange(self):
        if self.obj_bool:
            self.obj_value = self.amount_total

    def validated_inv(self, wizard):
        res = super(AccountInvoice, self).validated_inv(wizard)
        if res:
            if wizard.objected and self.obj_bool:
                return False

class AccountPaymentGroup(models.Model):
    _inherit = 'account.payment.group'

    objected_invoices_ids = fields.One2many('account.invoice.objected','apg_id',ondelete='cascade')

    @api.onchange('partner_id')
    def _objected_onchange(self):
        #self.invalidate_cache()
        #if self.objected_invoices_ids:
        #    self.objected_invoices_ids = (5, False, False)
        invs = self.env['account.invoice'].search([('partner_id','=',self.partner_id.id),('obj_bool','=',True)])

        self.objected_invoices_ids = False
        lines = list()
        for inv in invs:
            lines.append((0, False,  {'inv_id': inv.id,
                                                  'objected_amount': inv.obj_value,
                                                  'residual_amount': inv.residual-inv.obj_value,
                                                  'amount_currency': inv.amount_total,
                                                  'residual_amount_currency': inv.residual-inv.obj_value,
                                                  'currency_id': inv.currency_id.id,
                                                  'date': inv.date,
                                                  'duedate': inv.date_due,
                                                  'invoice_number': inv.display_name2,
                                                  'partner_id': inv.partner_id.id,
                                                  'total_amount': inv.amount_total}))
        self.objected_invoices_ids = lines


class AccountInvoiceObjected(models.Model):
    _name = 'account.invoice.objected'

    date = fields.Date(string="Date",translate=True)
    duedate = fields.Date(string="Due Date",translate=True)
    invoice_number = fields.Char(string="Invoice Number",translate=True)
    total_amount = fields.Monetary(string="Total Amount",translate=True,currency_field='currency_id')
    objected_amount = fields.Float(string="Objected Amount",translate=True)
    residual_amount = fields.Float(string="Residual Amount",translate=True)
    amount_currency = fields.Char(string="Amount Currencyt",translate=True)
    residual_amount_currency = fields.Char(string="Residual Amount Currencyt",translate=True)
    inv_id = fields.Many2one('account.invoice')
    partner_id = fields.Many2one('res.partner',string="partner",translate=True)
    currency_id = fields.Many2one('res.currency')
    apg_id = fields.Many2one('account.payment.group')


class ReportSlLedger(models.TransientModel):
    _inherit = 'report.sl.ledger'

    objected = fields.Boolean(string="Excluir Facturas Cuestionadas")
    extendedf = fields.Boolean()

    def get_filter(self):
        dic = super(ReportPlLedger, self).get_filter()
        if self.objected:
            dic.update({'objected':True})
        return dic

    @api.model
    def default_get(self, fields):
        values = super(ReportSlLedger, self).default_get(fields)
        flag = False
        conf = self.env['ir.config_parameter']
        if conf.get_param('check.add_obj_inv') == 'True':
            flag = True
        values['extendedf'] = flag
        return values

    def get_xls_domain(self,wizard):
        domain = super(ReportSlLedger, self).get_xls_domain()
        if self.objected:
            domain.append(('obj_bool', '!=', False))
        return domain

class ReportPlLedger(models.TransientModel):
    _inherit = 'report.pl.ledger'

    objected = fields.Boolean(string="Excluir Facturas Cuestionadas")
    extendedf = fields.Boolean()

    def get_filter(self):
        dic = super(ReportPlLedger, self).get_filter()
        if self.objected:
            dic.update({'objected':True})
        return dic

    @api.model
    def default_get(self, fields):
        values = super(ReportPlLedger, self).default_get(fields)
        flag = False
        conf = self.env['ir.config_parameter']
        if conf.get_param('check.add_obj_inv') == 'True':
            flag = True
        values['extendedf'] = flag
        return values