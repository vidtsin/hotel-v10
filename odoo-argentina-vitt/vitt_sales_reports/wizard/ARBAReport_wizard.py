from datetime import datetime
from dateutil import relativedelta
from odoo import http, models, fields, api, _
from cStringIO import StringIO
import base64
from decimal import *
import time
from . import VATReport_wizard
import string
from odoo.exceptions import ValidationError, Warning

TWOPLACES = Decimal(10) ** -2

def parse(str):
    printable = set(string.printable)
    tstr =  filter(lambda x: x in printable, str)
    return tstr[:30]

def MultiplybyRate(rate, amountincur, curcomp, invcur):
    if curcomp != invcur:
        total =  float(rate) * float(amountincur)
    else:
        total = amountincur

    total = Decimal(total).quantize(TWOPLACES)
    total *= 100
    longtotal = long(total)
    return longtotal

def MultiplybyRate2(rate, amountincur, curcomp, invcur):
    str1 = ""
    if curcomp != invcur:
        total =  float(rate) * float(amountincur)
    else:
        total = amountincur

    total = Decimal(total).quantize(TWOPLACES)
    str1 = str(total)
    str1 = str1.replace(".",",")
    return str1

def converttolong(amount):
    if amount < 0:
        amount = -amount
    return long(amount*100)

class sire_report(models.TransientModel):
    _name = 'arba.report.wizard'

    wh_code = fields.Many2one('account.tax',string='Cod Retencion',
        domain="[('type_tax_use','=','supplier'),('jurisdiction_code','!=',False),('tax_group_id.tax','=','gross_income'),('tax_group_id.application','=','provincial_taxes'),('tax_group_id.type','=','withholding')]")
    date_from = fields.Date(string='Date From', required=True,
        default=datetime.now().strftime('%Y-%m-01'))
    date_to = fields.Date(string='Date To', required=True,
        default=str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])
    percep_code = fields.Many2many('account.tax',string='Cod Percepcion',
        domain="[('type_tax_use','=','sale'),('jurisdiction_code','!=',False),('tax_group_id.tax','=','gross_income'),('tax_group_id.application','=','provincial_taxes'),('tax_group_id.type','=','perception')]")
    oper_type = fields.Selection([('A','Alta'),('B','Baja'),('M','Modificado')],string="Tipo de Operacion")
    percep = fields.Boolean()
    wh = fields.Boolean()

    def arba_wh_to_txt(self):
        if not self.wh_code:
            raise Warning(_('Debe Completar al menos un codigo de Retencion'))

        payments = self.env['account.payment']
        domain = [('payment_date', '<=', self.date_to), ('payment_date', '>=', self.date_from),
                  ('tax_withholding_id', 'in', list(self.wh_code._ids)), ('state', '!=', 'draft')]


        filename1 = "arba_retenciones.txt"
        context = self._context
        t1 = int()
        str = ""
        str2 = ""

        payments = payments.search(domain,order="payment_date")
        for pay in payments:
            str2 = ""
            if pay.withholding_number:
                str2 = pay.withholding_number
            str += pay.vendorbill.partner_id.main_id_number [0:2] + "-" + pay.vendorbill.partner_id.main_id_number[2:10] + "-" + pay.vendorbill.partner_id.main_id_number[10:11]
            str += pay.payment_date[8:10] + '/' + pay.payment_date[5:7] + '/' + pay.payment_date[0:4]
            if str2:
                if '-' in str2:
                    str += "{:0>4}".format(str2.split('-')[0])
                    str += "{:0>8}".format(str2.split('-')[1])
                else:
                    str += "{:0>12}".format(str2[-12:])
            else:
                str += "000000000000"
            t1 = MultiplybyRate2(1, pay.amount, pay.company_id.currency_id, pay.currency_id)
            str += "{:0>11}".format(t1)
            str += "{:?>1}".format(self.oper_type)
            str += '\r\n'

        fp = StringIO()
        fp.write(str)
        export_id = self.env['sicore.extended'].create({'excel_file2': base64.encodestring(fp.getvalue()), 'file_name2': filename1}).id
        fp.close()
        return{
            'view_mode': 'form',
            'res_id': export_id,
            'res_model': 'sicore.extended',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'context': context,
            'target': 'new',
        }


    def arba_percep_to_txt(self):
        if not self.percep_code:
            raise Warning(_('Debe Completar al menos un codigo de Percepcion'))

        invoices = self.env['account.invoice']
        domain = [('state', 'in', ['open', 'paid']), ('type', 'in', ['out_invoice','out_refund']),
                  ('date_invoice', '<=', self.date_to), ('date_invoice', '>=', self.date_from),
                  #('tax_line_ids', 'in', list(self.percep_code._ids))
                  ]

        invoices = invoices.search(domain, order="date_invoice")

        filename1 = "arba_percepciones.txt"
        context = self._context
        t1 = int()
        str = ""
        for inv in invoices:
            taxes = inv.tax_line_ids.filtered(lambda x: x.tax_id.id in list(self.percep_code._ids))
            if any(tax.amount > 0 for tax in taxes):
                str += inv.partner_id.main_id_number [0:2] + "-" + inv.partner_id.main_id_number[2:10] + "-" + inv.partner_id.main_id_number[10:11]
                str += inv.date_invoice[8:10] + '/' + inv.date_invoice[5:7] + '/' + inv.date_invoice[0:4]
                if inv.document_type_id.internal_type == 'invoice':
                    str += "F"
                elif inv.document_type_id.internal_type == 'credit_note':
                    str += "C"
                elif inv.document_type_id.internal_type == 'debit_note':
                    str += "D"
                else:
                    str += "?"
                str += inv.journal_document_type_id.document_type_id.document_letter_id.name
                str += "{:0>5}".format(inv.journal_id.point_of_sale_number)
                str += "{:0>8}".format(inv.document_number[5:])

                t1 = MultiplybyRate2(inv.currency_rate, inv.amount_untaxed, inv.company_currency_id, inv.currency_id)
                if inv.type != 'out_refund':
                    str += "{:0>12}".format(t1)
                else:
                    str += "-" + "{:0>11}".format(t1)

                t1 = MultiplybyRate2(inv.currency_rate, sum(taxes.mapped('amount')), inv.company_currency_id, inv.currency_id)
                if inv.type != 'out_refund':
                    str += "{:0>11}".format(t1)
                else:
                    str += "-" + "{:0>10}".format(t1)

                str += "{:?>1}".format(self.oper_type)
                str += '\r\n'

        fp = StringIO()
        fp.write(str)
        export_id = self.env['sicore.extended'].create({'excel_file': base64.encodestring(fp.getvalue()), 'file_name': filename1}).id
        fp.close()
        return{
            'view_mode': 'form',
            'res_id': export_id,
            'res_model': 'sicore.extended',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'context': context,
            'target': 'new',
        }
