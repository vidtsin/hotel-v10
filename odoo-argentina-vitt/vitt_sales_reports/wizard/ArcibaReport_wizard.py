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
import unicodedata

TWOPLACES = Decimal(10) ** -2


def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    printable = set(string.printable)
    res =  u"".join([c for c in nfkd_form if not unicodedata.combining(c)])[:30]
    return filter(lambda x: x in printable, res)


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
    if curcomp != invcur:
        total =  float(rate) * float(amountincur)
    else:
        total = amountincur

    total = Decimal(total).quantize(TWOPLACES)
    str1 = str(total).replace('.',',')

    return str1


def converttolong(amount):
    if amount < 0:
        amount = -amount
    return long(amount*100)

class sire_report2(models.TransientModel):
    _name = 'arciba2.report.wizard'

    tax_ids = fields.Many2many('account.tax', 'a7', 'b7', 'c7',
        string='Taxes',
        domain="[('type_tax_use','=','purchase'),('jurisdiction_code','!=',False)]")
    date_from = fields.Date(string='Date From', required=True,
        default=datetime.now().strftime('%Y-%m-01'))
    date_to = fields.Date(string='Date To', required=True,
        default=str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])
    jurisdiction_code_ids = fields.Many2many('jurisdiction.codes',string='codigo jurisdiccion')

    def arciba2_to_txt(self):
        str = ""
        filename1 = "sifere_customs_preceptions.txt"
        context = self._context

        if self.tax_ids and self.jurisdiction_code_ids:
            raise Warning(_('Debe Completar solo 1 campo, jurisdiccion o impuesto'))
        if not self.tax_ids and not self.jurisdiction_code_ids:
            raise Warning(_('Debe Completar al menos 1 campo, jurisdiccion o impuesto'))

        invoices = self.env['account.invoice']
        domain = [('state', 'in', ['open', 'paid']), ('type', 'in', ['in_invoice']),
                  ('date_invoice', '<=', self.date_to), ('date_invoice', '>=', self.date_from),
                  ('journal_document_type_id.document_type_id.document_letter_id.name','=','I')]
        # if self.jurisdiction_code_ids:
        #     taxes = self.env['account.tax'].search([('jurisdiction_code', 'in', self.jurisdiction_code_ids._ids)])
        #     print taxes
        #     domain.append(('tax_line_ids._ids', 'in', list(taxes._ids)))
        # if self.tax_ids:
        #     domain.append(('tax_line_ids', 'in', list(self.tax_ids._ids)))
        invoices = invoices.search(domain, order="date_invoice")
        for inv in invoices:
            for tax in inv.tax_line_ids:
                if tax.tax_id.jurisdiction_code in self.jurisdiction_code_ids or tax.tax_id in self.tax_ids:
                    str += tax.tax_id.jurisdiction_code.name
                    str += "{:0>13}".format(inv.partner_id.main_id_number[0:2] + "-" + inv.partner_id.main_id_number[2:10] + "-" + inv.partner_id.main_id_number[10:11])
                    str += inv.date_invoice[8:10] + '/' + inv.date_invoice[5:7] + '/' + inv.date_invoice[0:4]
                    str += "{:0>20}".format(inv.document_number)
                    t1 = MultiplybyRate2(inv.currency_rate, tax.amount, inv.company_currency_id, inv.currency_id)
                    str += "{:0>10}".format(t1)
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



class sire_report(models.TransientModel):
    _name = 'arciba.report.wizard'

    wh_code = fields.Many2one('account.tax',string='Cod Retencion',
        domain="[('type_tax_use','=','supplier'),('sicore_norm','!=',False),('tax_group_id.tax','=','gross_income'),('tax_group_id.application','=','provincial_taxes'),('tax_group_id.type','=','withholding')]")
    date_from = fields.Date(string='Date From', required=True,
        default=datetime.now().strftime('%Y-%m-01'))
    date_to = fields.Date(string='Date To', required=True,
        default=str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])
    percep_code = fields.Many2one('account.tax',string='Cod Percepcion',
        domain="[('type_tax_use','=','sale'),('sicore_norm','!=',False),('tax_group_id.tax','=','gross_income'),('tax_group_id.application','=','provincial_taxes'),('tax_group_id.type','=','perception')]")
    do_percep = fields.Boolean(string="Withholdings",default=True,translate=True)
    do_wh = fields.Boolean(string="Perceptions",default=True,translate=True)


    def do_percepf(self,invoices,nc=False):
        t1 = 0
        str1 = ""
        aux = ""

        for inv in invoices:
            for code in inv.tax_line_ids:
                if code.tax_id.id in list(self.percep_code._ids):
                    if nc:
                        str1 += "2"
                        str1 += "{:0>4}".format(inv.document_number[0:4]) + "{:0>8}".format(inv.document_number[5:])
                        str1 += inv.date_invoice[8:10] + '/' + inv.date_invoice[5:7] + '/' + inv.date_invoice[0:4]
                        t1 = MultiplybyRate(inv.currency_rate, (inv.amount_total - code.amount), inv.company_currency_id,
                                            inv.currency_id)
                        str1 += "{:0>16}".format(t1)
                        str1 += "{:>16}".format(" ")

                        orig = self.env['account.invoice'].search([('id','=',inv.refund_invoice_id.id)])
                        if orig.document_type_id.internal_type == 'invoice':
                            str1 += "01"
                        elif orig.document_type_id.internal_type == 'debit_note':
                            str1 += "02"
                        else:
                            str1 += "??"
                        str1 += inv.document_type_id.document_letter_id.name

                        nc_orig = self.env['account.invoice'].search([('id','=',inv.nc_ref_id)])
                        if nc_orig:
                            str1 += "{:0>8}".format(nc_orig.document_number[0:4]) + "{:0>8}".format(nc_orig.document_number[5:])
                            str1 += "{0:>10}".format(nc_orig.partner_id.main_id_number)
                        else:
                            str1 += "{:0>16}".format('0')
                            str1 += "{0:>10}".format('0')
                        str1 += "{:0>3}".format(code.tax_id.sicore_norm.name)
                        str1 += inv.date_invoice[8:10] + '/' + inv.date_invoice[5:7] + '/' + inv.date_invoice[0:4]
                        t1 = MultiplybyRate(inv.currency_rate, code.amount, inv.company_currency_id, inv.currency_id)
                        str1 += "{:0>16}".format(t1)
                        t1 = MultiplybyRate(inv.currency_rate, (code.amount / code.base * 100), inv.company_currency_id,
                                            inv.currency_id)
                        str1 += "{:0>5}".format(t1)

                    else:
                        str1 += "2"
                        str1 += "{:0>3}".format(code.tax_id.sicore_norm.name)
                        str1 += inv.date_invoice[8:10] + '/' + inv.date_invoice[5:7] + '/' + inv.date_invoice[0:4]
                        if inv.document_type_id.internal_type == 'invoice':
                            str1 += "01"
                        elif inv.document_type_id.internal_type == 'debit_note':
                            str1 += "02"
                        else:
                            str1 += "??"

                        str1 += inv.document_type_id.document_letter_id.name
                        str1 += "{:0>8}".format(inv.document_number[0:4]) + "{:0>8}".format(inv.document_number[5:])
                        str1 += inv.date_invoice[8:10] + '/' + inv.date_invoice[5:7] + '/' + inv.date_invoice[0:4]

                        t1 = MultiplybyRate(inv.currency_rate, (inv.amount_total - code.amount), inv.company_currency_id,
                                            inv.currency_id)
                        str1 += "{:0>16}".format(t1)

                        str1 += "{:>16}".format(" ")
                        if inv.partner_id.main_id_category_id.arciba_doc_code:
                            str1 += inv.partner_id.main_id_category_id.arciba_doc_code
                        else:
                            str1 += "?"
                        str1 += "{0:>10}".format(inv.partner_id.main_id_number)

                        if inv.partner_id.gross_income_type == 'multilateral':
                            str1 += "2"
                        elif inv.partner_id.gross_income_type == 'local':
                            str1 += "1"
                        elif inv.partner_id.gross_income_type == 'no_liquida':
                            str1 += "4"
                        elif inv.partner_id.gross_income_type == 'regimen_simplificado':
                            str1 += "5"
                        else:
                            str1 += "?"

                        if inv.partner_id.gross_income_type == 'no_liquida':
                            str1 += "{:0>11}".format("0")
                        else:
                            if inv.partner_id.gross_income_number:
                                aux = inv.partner_id.gross_income_number.replace("-","")
                            else:
                                aux = ""
                            str1 += "{:0>11}".format(aux)

                        str1 += "{:0>1}".format(inv.partner_id.afip_responsability_type_id.arciba_resp_code)

                        tmpstr = remove_accents(inv.partner_id.name)

                        str1 += "{:>30}".format(tmpstr)
                        str1 += "{:0>16}".format("0")

                        #t1 = MultiplybyRate(inv.currency_rate, (inv.amount_total - code.amount), inv.company_currency_id,
                        #                    inv.currency_id)
                        #str1 += "{:0>16}".format(t1)

                        if inv.document_type_id.document_letter_id.name in ['A','M']:
                            t1 = sum(inv.tax_line_ids.filtered(lambda r: (r.tax_id.tax_group_id.type == 'tax' and
                                    r.tax_id.tax_group_id.tax == 'vat') and r.tax_id.tax_group_id.application == 'national_taxes' and
                                    r.tax_id.amount in [2.5, 5, 10.5, 21, 27]).mapped('amount'))
                        else:
                            t1 = 0
                        t1 = MultiplybyRate(inv.currency_rate, t1, inv.company_currency_id, inv.currency_id)
                        str1 += "{:0>16}".format(t1)

                        t1 = sum(inv.tax_line_ids.filtered(lambda r: (
                                r.tax_id.tax_group_id.type == 'perception' and
                                r.tax_id.tax_group_id.tax == 'gross_income') and
                                r.tax_id.tax_group_id.application == 'provincial_taxes' and
                                r.tax_id.id == self.percep_code.id).mapped('base'))
                        t1 = MultiplybyRate(inv.currency_rate, t1, inv.company_currency_id, inv.currency_id)
                        str1 += "{:0>16}".format(t1)

                        t1 = MultiplybyRate(inv.currency_rate, (code.amount / code.base * 100), inv.company_currency_id,
                                            inv.currency_id)
                        str1 += "{:0>5}".format(t1)

                        t1 = MultiplybyRate(inv.currency_rate, code.amount, inv.company_currency_id, inv.currency_id)
                        str1 += "{:0>16}".format(t1)
                        str1 += "{:0>16}".format(t1)
                    str1 += '\r\n'
        return str1

    def arciba_to_txt(self):
        if self.do_percep and not self.percep_code:
            raise Warning(_('Debe Completar al menos un codigo de Percepcion'))
        if self.do_wh and not self.wh_code:
            raise Warning(_('Debe Completar al menos un codigo de Retencion'))

        t1 = 0
        str1 = ""
        str2 = ""
        filename1 = "ARCIBA_retenciones_percepciones.txt"
        filename2 = "ARCIBA_notas_credito.txt"
        context = self._context


        #file1
        if self.do_percep:
            invoices = self.env['account.invoice']
            domain = [('state','in',['open','paid']),('type','in',['out_invoice']),
                      ('date_invoice','<=',self.date_to),('date_invoice','>=',self.date_from)]

            invoices = invoices.search(domain,order="date_invoice")
            str1 = self.do_percepf(invoices,nc=False)

        if self.do_wh:
            payments = self.env['account.payment']
            domain = [('payment_date','<=',self.date_to),('payment_date','>=',self.date_from),
                      ('tax_withholding_id.id','in',list(self.wh_code._ids)),('state','!=','draft')]
            payments = payments.search(domain,order='payment_date')
            aux = ""

            for pay in payments:
                str1 += "1"
                str1 += "{:0>3}".format(pay.tax_withholding_id.sicore_norm.name)
                str1 += pay.payment_date[8:10] + '/' + pay.payment_date[5:7] + '/' + pay.payment_date[0:4]
                if pay.vendorbill.document_type_id.internal_type == 'invoice':
                    str1 += "01"
                elif pay.vendorbill.document_type_id.internal_type == 'debit_note':
                    str1 += "02"
                else:
                    str1 += "??"

                str1 += pay.vendorbill.document_type_id.document_letter_id.name
                str1 += "{:0>8}".format(pay.vendorbill.document_number[0:4]) + "{:0>8}".format(pay.vendorbill.document_number[5:])
                str1 += pay.vendorbill.date_invoice[8:10] + '/' + pay.vendorbill.date_invoice[5:7] + '/' + pay.vendorbill.date_invoice[0:4]

                t1 = pay.payment_group_id.payments_amount
                t1 = MultiplybyRate(pay.vendorbill.currency_rate, t1, pay.vendorbill.company_currency_id, pay.currency_id)
                str1 += "{:0>16}".format(t1)

                str1 += "{:>16}".format(pay.withholding_number)
                if pay.vendorbill.partner_id.main_id_category_id.arciba_doc_code:
                    str1 += pay.vendorbill.partner_id.main_id_category_id.arciba_doc_code
                else:
                    str1 += "?"
                str1 += "{0:>10}".format(pay.vendorbill.partner_id.main_id_number)
                if pay.vendorbill.partner_id.gross_income_type == 'multilateral':
                    str1 += "2"
                elif pay.vendorbill.partner_id.gross_income_type == 'local':
                    str1 += "1"
                elif pay.vendorbill.partner_id.gross_income_type == 'no_liquida':
                    str1 += "4"
                elif pay.vendorbill.partner_id.gross_income_type == 'regimen_simplificado':
                    str1 += "5"
                else:
                    str1 += "?"

                if pay.vendorbill.partner_id.gross_income_type == 'no_liquida':
                    str1 += "{:0>11}".format("0")
                else:
                    if pay.vendorbill.partner_id.gross_income_number:
                        aux = pay.vendorbill.partner_id.gross_income_number.replace("-", "")
                    else:
                        aux = ""
                str1 += "{:0>11}".format(aux)
                str1 += "{:0>1}".format(pay.vendorbill.partner_id.afip_responsability_type_id.arciba_resp_code)

                tmpstr = remove_accents(pay.vendorbill.partner_id.name)

                str1 += "{:>30}".format(tmpstr)
                str1 += "{:0>16}".format("0")

                t1 = sum(pay.vendorbill.tax_line_ids.filtered(lambda r: (r.tax_id.tax_group_id.type == 'tax' and
                    r.tax_id.tax_group_id.tax == 'vat') and r.tax_id.tax_group_id.application == 'national_taxes' and
                    r.tax_id.amount in [2.5, 5, 10.5, 21, 27]).mapped('amount'))
                t1 = MultiplybyRate(pay.vendorbill.currency_rate, t1, pay.vendorbill.company_currency_id, pay.currency_id)
                str1 += "{:0>16}".format(t1)

                t1 = MultiplybyRate(pay.vendorbill.currency_rate, pay.withholding_base_amount, pay.vendorbill.company_currency_id,pay.currency_id)
                str1 += "{:0>16}".format(t1)

                str1 += "{:0>5}".format(str(pay.wh_perc*10).replace('.',''))

                t1 = MultiplybyRate(pay.vendorbill.currency_rate, pay.amount, pay.vendorbill.company_currency_id,pay.currency_id)
                str1 += "{:0>16}".format(t1)
                str1 += "{:0>16}".format(t1)
                str1 += '\r\n'

        #file2
        if self.do_percep:
            invoices = self.env['account.invoice']
            domain = [('state','in',['open','paid']),('type','in',['out_refund']),
                      ('date_invoice','<=',self.date_to),('date_invoice','>=',self.date_from)]

            invoices = invoices.search(domain,order="date_invoice")
            str2 = self.do_percepf(invoices,nc=True)

        fp = StringIO()
        fp2 = StringIO()
        fp.write(str1)
        fp2.write(str2)
        export_id = self.env['sicore.extended'].create({'excel_file': base64.encodestring(fp.getvalue()), 'file_name': filename1,
                                                        'excel_file2': base64.encodestring(fp2.getvalue()),'file_name2': filename2}).id
        fp.close()
        fp2.close()
        return {
            'view_mode': 'form',
            'res_id': export_id,
            'res_model': 'sicore.extended',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'context': context,
            'target': 'new',
        }
