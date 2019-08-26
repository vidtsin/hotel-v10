# -*- coding: utf-8 -*-
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

def converttolong(amount):
    if amount < 0:
        amount = -amount
    return long(amount*100)

class excel_citi_extended(models.TransientModel):
    _name= "excel.citi.extended"
    excel_file_p_cbte = fields.Binary('Download')
    file_name_p_cbte = fields.Char('REGINFO_CV_COMPRAS_CBTE', size=64)
    excel_file_p_alic = fields.Binary('Download')
    file_name_p_alic = fields.Char('REGINFO_CV_COMPRAS_ALICUOTAS', size=64)
    excel_file_p_imp = fields.Binary('Download')
    file_name_p_imp = fields.Char('REGINFO_CV_COMPRAS_IMPORTACIONES', size=64)
    excel_file_v_cbte = fields.Binary('Download')
    file_name_v_cbte = fields.Char('REGINFO_CV_VENTAS_CBTE', size=64)
    excel_file_v_alic = fields.Binary('Download')
    file_name_v_alic = fields.Char('REGINFO_CV_VENTAS_ALICUOTAS', size=64)
    errors = fields.Binary('Errores')
    file_errors = fields.Char('Errores', size=64)


class citi_reports(models.TransientModel):
    _name = 'vitt_sales_reports.reportciti'

    date_from = fields.Date(string='Date From', required=True,
        default=datetime.now().strftime('%Y-%m-01'))
    date_to = fields.Date(string='Date To', required=True,
        default=str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])

    def getvatarray(self):
        r = {}
        ARRAYVAT = self.env['account.tax'].search([])
        for code in ARRAYVAT:
            r.update({code.id: code.tax_group_id.afip_code})
        return r

    def getallcodes(self,invoice=None):
        if invoice!=None:
            self = invoice
        return self.tax_line_ids.filtered(lambda r: (
            r.tax_id.tax_group_id.type == 'tax' and
            r.tax_id.tax_group_id.tax == 'vat') and
            (r.tax_id.tax_group_id.afip_code != 1 and
            r.tax_id.tax_group_id.afip_code != 2)).mapped('tax_id.id')

    def getallcodes2(self,invoice=None):
        if invoice!=None:
            self = invoice
        return self.tax_line_ids.filtered(lambda r: (
            r.tax_id.tax_group_id.type == 'tax' and
            r.tax_id.tax_group_id.tax == 'vat') and
            (r.tax_id.tax_group_id.afip_code == 1 or
            r.tax_id.tax_group_id.afip_code == 2)).mapped('tax_id.id')

    def getallcodessl(self,invoice=None):
        if invoice!=None:
            self = invoice
        return self.tax_line_ids.filtered(lambda r: (
            r.tax_id.tax_group_id.type == 'tax' and
            r.tax_id.tax_group_id.tax == 'vat') and
            (r.tax_id.tax_group_id.afip_code == 1 or
             r.tax_id.tax_group_id.afip_code == 2 or
             r.tax_id.tax_group_id.afip_code == 3)).mapped('tax_id.id')

    def getallcodesimp(self,invoice=None):
        if invoice!=None:
            self = invoice
        res = []
        for taxes in self.tax_line_ids:
            if taxes.invoice_id.id == self.id:
                if taxes.tax_id.tax_group_id.type == 'tax' and taxes.tax_id.tax_group_id.tax == 'vat' and \
                        (taxes.tax_id.tax_group_id.afip_code in [3,4,5,6,8,9]):
                    res.append(taxes.tax_id.id)
        return res
        #return self.tax_line_ids.filtered(lambda r: (
        #    r.tax_id.tax_group_id.type == 'tax' and
        #    r.tax_id.tax_group_id.tax == 'vat')).mapped('name')

    def getvatafipcode(self, invoice=None,vatcode=None):
        if invoice != None:
            self = invoice
        for taxes in self.tax_line_ids:
            if taxes.invoice_id.id == self.id and taxes.tax_id.id==vatcode:
                res = taxes.tax_id.tax_group_id.afip_code
        return res


    def gettotforcode(self,invoice=None,vatcode=None):
        if invoice!=None:
            self = invoice
        return sum(self.tax_line_ids.filtered(lambda r: (
            r.tax_id.tax_group_id.type == 'tax' and
            r.tax_id.tax_group_id.tax == 'vat') and
            r.tax_id.tax_group_id.afip_code == vatcode ).mapped('amount'))

    def gettotforcodeimp(self,invoice=None,vatcode=None):
        if invoice!=None:
            self = invoice
        return sum(self.tax_line_ids.filtered(lambda r: (
            r.tax_id.tax_group_id.type == 'tax' and
            r.tax_id.tax_group_id.tax == 'vat') and
            r.tax_id.id == vatcode ).mapped('amount'))

    def getbaseforcode(self,invoice=None,vatcode=None):
        if invoice!=None:
            self = invoice
        return sum(self.tax_line_ids.filtered(lambda r: (
            r.tax_id.tax_group_id.type == 'tax' and
            r.tax_id.tax_group_id.tax == 'vat' and
            r.tax_id.tax_group_id.afip_code == vatcode)).mapped('base'))

    def getbaseforcodeimp(self,invoice=None,vatcode=None):
        if invoice!=None:
            self = invoice
        return sum(self.tax_line_ids.filtered(lambda r: (
            r.tax_id.tax_group_id.type == 'tax' and
            r.tax_id.tax_group_id.tax == 'vat' and
            r.tax_id.id == vatcode)).mapped('base'))

    def gettaxperc(self,code):
        invoiceModel = self.env['account.tax']
        tax = invoiceModel.search([('id', '=', code)])
        return tax.amount


    def getvatcodeslistg3(self,invoice=None):
        if invoice!=None:
            self = invoice
        return len(self.tax_line_ids.filtered(lambda r: (
            r.tax_id.tax_group_id.type == 'tax' and
            r.tax_id.tax_group_id.tax == 'vat') and
            (r.tax_id.tax_group_id.afip_code == 3 or
            r.tax_id.tax_group_id.afip_code == 4 or
            r.tax_id.tax_group_id.afip_code == 5 or
            r.tax_id.tax_group_id.afip_code == 6 or
            r.tax_id.tax_group_id.afip_code == 8 or
            r.tax_id.tax_group_id.afip_code == 9)).mapped('tax_id.id'))

    def getcodetype(self,invoice=None,code=None):
        res = ''
        if invoice != None:
            self = invoice
        for taxes in self.tax_line_ids:
            if taxes.tax_id.id==code:
                res = taxes.tax_id.tax_group_id.afip_code
        return res

    def getgrandtotalvat(self,invoice=None):
        if invoice!=None:
            self = invoice
        return sum(self.tax_line_ids.filtered(lambda r: (
            r.tax_id.tax_group_id.type == 'tax' and
            r.tax_id.tax_group_id.tax == 'vat') and
            (r.tax_id.tax_group_id.afip_code == 4 or
            r.tax_id.tax_group_id.afip_code == 3 or
            r.tax_id.tax_group_id.afip_code == 5 or
            r.tax_id.tax_group_id.afip_code == 6 or
            r.tax_id.tax_group_id.afip_code == 8 or
            r.tax_id.tax_group_id.afip_code == 9)).mapped('amount'))

    def getvatcodeslistg2(self,invoice=None):
        if invoice!=None:
            self = invoice
        return len(self.tax_line_ids.filtered(lambda r: (
            r.tax_id.tax_group_id.type == 'tax' and
            r.tax_id.tax_group_id.tax == 'vat') and
            (r.tax_id.tax_group_id.afip_code != 4 and
            r.tax_id.tax_group_id.afip_code != 3 and
            r.tax_id.tax_group_id.afip_code != 5 and
            r.tax_id.tax_group_id.afip_code != 6 and
            r.tax_id.tax_group_id.afip_code != 8 and
            r.tax_id.tax_group_id.afip_code == 2 and
            r.tax_id.tax_group_id.afip_code != 9)).mapped('tax_id.id'))


    def validate_data(self,invs,sale=False):
        res = []
        conf = self.env['ir.config_parameter']
        if sale:
            c_value = conf.get_param('check.citi_sl_box')
        else:
            c_value = conf.get_param('check.citi_pl_box')
        if c_value == 'True':
            for inv in invs:
                if inv.journal_id.use_documents:
                    if not inv.journal_document_type_id.document_type_id.code:
                        res.append("falta tipo de documento en factura " + inv.display_name)
                if not inv.partner_id.main_id_category_id.name:
                    res.append("falta Codigo de Tipo de Documento del Proveedor/Cliente " + inv.display_name)
                if not inv.partner_id.main_id_number:
                    res.append("falta Numero de Identificacion del Proveedor/Cliente " + inv.display_name)
                if not inv.currency_id.afip_code:
                    res.append("falta codigo afip para moneda " + inv.display_name)
                if inv.currency_id != inv.company_currency_id and not inv.currency_rate:
                    res.append("falta tipo de cambio " + inv.display_name)
                if not inv.partner_id.name:
                    res.append("falta nombre de partner " + inv.display_name)
        return res


    def Print_citi(self):
        tstr = ""
        tstr_alic = ""
        tstr_p_imp = ""
        tstr_v_cbte = ""
        tstr_v_alic = ""

        context = self._context
        gARRAYVAT = self.getvatarray()
        #purchase ledger
        domain = [
            '&',('date', '>=', self.date_from),('date', '<=', self.date_to),
            ('type', '!=', 'out_invoice'),('type', '!=', 'out_refund'),'|',('state', '=', 'open'),
            ('state', '=', 'paid')
        ]
        invoiceModel = self.env['account.invoice']
        invoices = invoiceModel.search(domain,order="date_invoice")
        #doc_ids = invoices._ids
        filename_p_cbte = 'REGINFO_CV_COMPRAS_CBTE.txt'
        filename_p_alic = 'REGINFO_CV_COMPRAS_ALICUOTAS.txt'
        filename_p_imp = 'REGINFO_CV_COMPRAS_IMPORTACIONES.txt'
        filename_v_cbte = 'REGINFO_CV_VENTAS_CBTE.txt'
        filename_v_alic = 'REGINFO_CV_VENTAS_ALICUOTAS.txt'


        pdata = self.validate_data(invoices,sale=False)


        #REGINFO_CV_COMPRAS_CBTE
        for inv in invoices:
            if inv.journal_id.use_documents:
                tstr = tstr + inv.date_invoice[0:4] + inv.date_invoice[5:7] + inv.date_invoice[8:10]
                tstr = tstr + "{:0>3}".format(inv.journal_document_type_id.document_type_id.code)
                if "{:0>3}".format(inv.journal_document_type_id.document_type_id.code) != '066' \
                    and "{:0>3}".format(inv.journal_document_type_id.document_type_id.code) != '067':

                    nr = inv.document_number.split('-')
                    tstr = tstr + "{:0>5}".format(nr[0]) + "{:0>20}".format(nr[1])
                    tstr = tstr + "{:>16}".format(' ')
                else:
                    tstr = tstr + "{:0>25}".format('0')
                    tstr = tstr + "{:0>16}".format(inv.document_number)
                tstr = tstr + "{:0>2}".format(inv.partner_id.main_id_category_id.afip_code)
                tstr = tstr + "{:0>20}".format(inv.partner_id.main_id_number)

                tmpstr = remove_accents(inv.partner_id.name)

                tstr = tstr + "{:<30}".format(tmpstr)

                total = MultiplybyRate(inv.currency_rate, inv.amount_total, inv.company_currency_id, inv.currency_id)
                tstr = tstr + "{:0>15}".format(total)

                if inv.journal_document_type_id.document_type_id.document_letter_id.name == 'B' or \
                        inv.journal_document_type_id.document_type_id.document_letter_id.name == 'C':
                    total = 0
                else:
                    total = converttolong(VATReport_wizard.def_sales_reports_reportvat.gettotnovat(inv))
                tstr = tstr + "{:0>15}".format(total)

                if inv.journal_document_type_id.document_type_id.document_letter_id.name == 'B' or \
                        inv.journal_document_type_id.document_type_id.document_letter_id.name == 'C':
                    total = 0
                else:
                    total = converttolong(VATReport_wizard.def_sales_reports_reportvat.gettotexempt(inv))
                tstr = tstr + "{:0>15}".format(total)

                total = converttolong(VATReport_wizard.def_sales_reports_reportvat.gettotpercep(inv))
                tstr = tstr + "{:0>15}".format(total)

                tstr = tstr + '000000000000000'

                total = converttolong(VATReport_wizard.def_sales_reports_reportvat.gettotgrossincome(inv))
                tstr = tstr + "{:0>15}".format(total)

                tstr = tstr + '000000000000000'

                total = converttolong(VATReport_wizard.def_sales_reports_reportvat.gettotinttaxes(inv))
                tstr = tstr + "{:0>15}".format(total)

                tstr = tstr + "{:>3}".format(inv.currency_id.afip_code)

                if inv.currency_id != inv.company_currency_id:
                    tstr = tstr + "{:0>10}".format(long(Decimal(inv.currency_rate).quantize(TWOPLACES)*1000000))
                else:
                    tstr = tstr + '0001000000'

                vatcodesqty = self.getvatcodeslistg3(inv)
                vatimp = self.getallcodes2(inv)
                if inv.journal_document_type_id.document_type_id.document_letter_id.name == 'B' or \
                        inv.journal_document_type_id.document_type_id.document_letter_id.name == 'C':
                    tstr = tstr + '0'
                elif len(vatimp) > 0 and vatcodesqty == 0:
                    tstr = tstr + '1'
                else:
                    tstr = tstr + str(vatcodesqty)

                if inv.fiscal_position_id.afip_code_purch == None:
                    tstr = tstr + '0'
                else:
                    tstr = tstr + "{:>1}".format(inv.fiscal_position_id.afip_code_purch)

                if inv.journal_document_type_id.document_type_id.document_letter_id.name != 'B' and \
                                inv.journal_document_type_id.document_type_id.document_letter_id.name != 'C':
                    total = self.getgrandtotalvat(inv)
                else:
                    total = 0
                total = MultiplybyRate(inv.currency_rate, total, inv.company_currency_id, inv.currency_id)
                tstr = tstr + "{:0>15}".format(total)

                tstr = tstr + "{:0>15}".format(0)
                tstr = tstr + "{:0>11}".format(0)
                tstr = tstr + "{:>30}".format(' ')
                tstr = tstr + "{:0>15}".format(0)
                tstr = tstr + '\r\n'

        #REGINFO_CV_COMPRAS_ALICUOTAS
        for inv in invoices:
            if "{:0>3}".format(inv.journal_document_type_id.document_type_id.code) not in [
                '066','067','006','007','008','006','009','010','011',
                '012','013','015','016','061','064','082','083','111',
                '113','114','116','117'] and inv.journal_id.use_documents:

                if inv.fiscal_position_id.afip_code == False:
                    vatcodes = self.getallcodes(inv)
                else:
                    vatcodes = self.getallcodes2(inv)

                for code in vatcodes:
                    tstr_alic += "{:0>3}".format(inv.document_type_id.code)
                    tmp = inv.document_number.split('-')
                    if len(tmp)==2:
                        tstr_alic += "{:0>5}".format(tmp[0]) + "{:0>20}".format(tmp[1])
                    else:
                        tstr_alic += "{:0>25}".format(tmp)
                    tstr_alic += "{:0>2}".format(inv.partner_id.main_id_category_id.afip_code)
                    tstr_alic += "{:0>20}".format(inv.partner_id.main_id_number)
                    if inv.fiscal_position_id.afip_code == False:
                        if code in gARRAYVAT:
                            total = self.getbaseforcode(inv,gARRAYVAT[code])
                        else:
                            total = 0
                    else:
                        total = 0

                    total = MultiplybyRate(inv.currency_rate, total, inv.company_currency_id, inv.currency_id)
                    tstr_alic += "{:0>15}".format(total)

                    if inv.fiscal_position_id.afip_code == False:
                        codetype = self.getcodetype(inv,code)
                        tstr_alic += "{:0>4}".format(codetype)
                    else:
                        tstr_alic += "{:0>4}".format('3')


                    if code in gARRAYVAT:
                        total = self.gettotforcode(inv,gARRAYVAT[code])
                    else:
                        total = 0
                    total = MultiplybyRate(inv.currency_rate, total, inv.company_currency_id, inv.currency_id)
                    tstr_alic += "{:0>15}".format(total)

                    #tstr_alic += "{:0>4}".format(long(self.gettaxperc(code)*100))
                    tstr_alic += '\r\n'

        #REGINFO_CV_COMPRAS_IMPORTACIONES
        for inv in invoices:
            if inv.journal_id.use_documents:
                if "{:0>3}".format(inv.journal_document_type_id.document_type_id.code) == '066' or \
                    "{:0>3}".format(inv.journal_document_type_id.document_type_id.code) == '067':

                    vatcodes = self.getallcodesimp(inv) #this is id of vatcode
                    for code in vatcodes:
                        tstr_p_imp += "{:0>15}".format(inv.document_number)

                        total = self.getbaseforcodeimp(inv,code)
                        total = MultiplybyRate(inv.currency_rate, total, inv.company_currency_id, inv.currency_id)
                        if total < 0:
                            total = total * -1
                            tstr_p_imp = tstr_p_imp + '-' +     "{:0>14}".format(total)
                        else:
                            tstr_p_imp = tstr_p_imp + "{:0>15}".format(total)

                        tstr_p_imp += "{:0>4}".format(self.getvatafipcode(inv,code))

                        total = self.gettotforcodeimp(inv,code)
                        total = MultiplybyRate(inv.currency_rate, total, inv.company_currency_id, inv.currency_id)
                        tstr_p_imp += "{:0>15}".format(total)

                        tstr_p_imp += '\r\n'

                    if "{:0>3}".format(inv.journal_document_type_id.document_type_id.code) == '066' and \
                        len(self.getallcodes2(inv))>=1 and len(vatcodes)==0:

                        tstr_p_imp += "{:0>15}".format(inv.document_number)

                        total = 0
                        tstr_p_imp = tstr_p_imp + "{:0>15}".format(total)

                        tstr_p_imp += "{:0>4}".format(0)

                        total = 0
                        tstr_p_imp += "{:0>15}".format(total)

                        tstr_p_imp += '\r\n'


        #sales ledger
        domain = [
            '&',('date', '>=', self.date_from),('date', '<=', self.date_to),
            ('type', '!=', 'in_invoice'),('type', '!=', 'in_refund'),'|',('state', '=', 'open'),
            ('state', '=', 'paid')
        ]
        invoiceModel = self.env['account.invoice']
        invoices = invoiceModel.search(domain,order="date_invoice")

        sdata = self.validate_data(invoices,sale=True)
        sdata += pdata

        if len(sdata)>0:
            perr = StringIO()
            std_err = ""
            for i,data in enumerate(sdata):
                std_err += sdata[i] + '\r\n'
            perr.write(std_err)
            export_id = self.env['excel.citi.extended'].create(
                {'errors': base64.encodestring(perr.getvalue())
                    , 'file_errors': 'errores.txt'}).id
            perr.close()
            return {
                'view_mode': 'form',
                'res_id': export_id,
                'res_model': 'excel.citi.extended',
                'view_type': 'form',
                'type': 'ir.actions.act_window',
                'context': context,
                'target': 'new',
            }

        #REGINFO_CV_VENTAS_CBTE
        for inv in invoices:
            if inv.journal_id.use_documents:
                tstr_v_cbte += inv.date_invoice[0:4] + inv.date_invoice[5:7] + inv.date_invoice[8:10]
                tstr_v_cbte += "{:0>3}".format(inv.journal_document_type_id.document_type_id.code)
                doc_nr = inv.document_number.split('-')
                tstr_v_cbte += "{:0>5}".format(doc_nr[0]) + "{:0>20}".format(doc_nr[1])
                tstr_v_cbte += "{:0>20}".format(doc_nr[1])
                tstr_v_cbte += "{:0>2}".format(inv.partner_id.main_id_category_id.afip_code)
                tstr_v_cbte += "{:0>20}".format(inv.partner_id.main_id_number)



                tmpstr = remove_accents(inv.partner_id.name)

                tstr_v_cbte += "{:<30}".format(tmpstr)

                total = MultiplybyRate(inv.currency_rate, inv.amount_total, inv.company_currency_id, inv.currency_id)
                tstr_v_cbte += "{:0>15}".format(total)

                total = converttolong(VATReport_wizard.def_sales_reports_reportvat.gettotnovat(inv))
                tstr_v_cbte += "{:0>15}".format(total)

                total = converttolong(VATReport_wizard.def_sales_reports_reportvat.gettotexempt(inv))
                tstr_v_cbte += "{:0>15}".format(total)

                total = converttolong(VATReport_wizard.def_sales_reports_reportvat.gettotpercep(inv))
                tstr_v_cbte += "{:0>15}".format(total)

                tstr_v_cbte += '000000000000000'

                total = converttolong(VATReport_wizard.def_sales_reports_reportvat.gettotgrossincome(inv))
                tstr_v_cbte += "{:0>15}".format(total)

                tstr_v_cbte += '000000000000000'

                total = converttolong(VATReport_wizard.def_sales_reports_reportvat.gettotinttaxes(inv))
                if total < 0:
                    total *= -1
                tstr_v_cbte += "{:0>15}".format(total)

                tstr_v_cbte += "{:>3}".format(inv.currency_id.afip_code)
                if inv.currency_id != inv.company_currency_id:
                    tstr_v_cbte += "{:0>10}".format(long(Decimal(inv.currency_rate).quantize(TWOPLACES)*1000000))
                else:
                    tstr_v_cbte += '0001000000'

                vatcodesqty = self.getvatcodeslistg3(inv)
                vatcodeex = self.getallcodes2(inv)

                if vatcodesqty > 0 and len(vatcodeex) >= 0:
                    tstr_v_cbte += str(vatcodesqty)
                elif vatcodesqty == 0 and len(vatcodeex) > 0:
                    tstr_v_cbte += '1'

                if inv.fiscal_position_id.afip_code == False:
                    tstr_v_cbte += '0'
                else:
                    tstr_v_cbte += "{:>1}".format(inv.fiscal_position_id.afip_code)

                tstr_v_cbte += '000000000000000'

                if inv.journal_document_type_id.document_type_id.document_letter_id.name != 'E' and \
                        inv.journal_document_type_id.document_type_id.code not in ["60","63","64","82","81"]:
                    tstr_v_cbte += inv.date_due[0:4] + inv.date_due[5:7] + inv.date_due[8:10]
                else:
                    tstr_v_cbte += '00000000'

                tstr_v_cbte += '\r\n'

        #REGINFO_CV_VENTAS_ALICUOTAS
        for inv in invoices:
            if inv.journal_id.use_documents:
                if "{:0>3}".format(inv.journal_document_type_id.document_type_id.code) != '066' and \
                    "{:0>3}".format(inv.journal_document_type_id.document_type_id.code) != '067':

                    #print "-----------"
                    if inv.fiscal_position_id.afip_code == False:
                        vatcodes = self.getallcodes(inv)
                        #print "sin posicion"
                    else:
                        #print "con posicion"
                        vatcodes = self.getallcodessl(inv)

                    #print inv.journal_document_type_id.document_type_id.code
                    #print inv.document_number
                    #print "vatcodes", vatcodes

                    for code in vatcodes:
                        tstr_v_alic += "{:0>3}".format(inv.document_type_id.code)
                        docnr = inv.document_number.split('-')
                        tstr_v_alic += "{:0>5}".format(docnr[0]) + "{:0>20}".format(docnr[1])
                        #tstr_v_alic += "{:0>2}".format(inv.partner_id.main_id_category_id.afip_code)
                        #tstr_v_alic += "{:0>20}".format(inv.partner_id.main_id_number)
                        if inv.fiscal_position_id.afip_code == False:
                            if code in gARRAYVAT:
                                total = self.getbaseforcode(inv,gARRAYVAT[code])
                            else:
                                total = 0
                        else:
                            if inv.journal_document_type_id.document_type_id.document_letter_id.name != 'E':
                                total = 0
                            else:
                                total = self.getbaseforcode(inv, gARRAYVAT[code])

                        total = MultiplybyRate(inv.currency_rate, total, inv.company_currency_id, inv.currency_id)
                        tstr_v_alic += "{:0>15}".format(total)

                        if inv.fiscal_position_id.afip_code == False:
                            codetype = self.getcodetype(inv, code)
                            tstr_v_alic += "{:0>4}".format(codetype)
                        else:
                            tstr_v_alic += "{:0>4}".format('3')

                        if code in gARRAYVAT:
                            total = self.gettotforcode(inv,gARRAYVAT[code])
                        else:
                            total = 0
                        total = MultiplybyRate(inv.currency_rate, total, inv.company_currency_id, inv.currency_id)
                        tstr_v_alic += "{:0>15}".format(total)

                        tstr_v_alic += '\r\n'


        fp_alic = StringIO()
        fp_cbte = StringIO()
        fp_imp = StringIO()
        fp_v_cbte = StringIO()
        fp_v_alic = StringIO()

        fp_cbte.write(tstr)
        fp_alic.write(tstr_alic)
        fp_imp.write(tstr_p_imp)
        fp_v_cbte.write(tstr_v_cbte)
        fp_v_alic.write(tstr_v_alic)
        export_id = self.env['excel.citi.extended'].create({'excel_file_p_cbte': base64.encodestring(fp_cbte.getvalue())
                                                            , 'file_name_p_cbte': filename_p_cbte
                                                            , 'excel_file_p_alic': base64.encodestring(fp_alic.getvalue())
                                                            , 'file_name_p_alic': filename_p_alic
                                                            , 'excel_file_p_imp': base64.encodestring(fp_imp.getvalue())
                                                            , 'file_name_p_imp': filename_p_imp
                                                            , 'excel_file_v_cbte': base64.encodestring(fp_v_cbte.getvalue())
                                                            , 'file_name_v_cbte': filename_v_cbte
                                                            , 'excel_file_v_alic': base64.encodestring(fp_v_alic.getvalue())
                                                            , 'file_name_v_alic': filename_v_alic}).id
        fp_cbte.close()
        fp_alic.close()
        fp_imp.close()
        fp_v_cbte.close()
        fp_v_alic.close()
        return{
            'view_mode': 'form',
            'res_id': export_id,
            'res_model': 'excel.citi.extended',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'context': context,
            'target': 'new',
        }



#controls by nl_settings CITI
class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    @api.constrains('date_due')
    def on_save_date_due(self):
        if not self.date_due:
            doit = False
            if self.journal_id.type == 'sale' and self.journal_id.use_documents:
                conf = self.env['ir.config_parameter']
                c_value = conf.get_param('check.citi_sl_box')
                if c_value == "True":
                    doit = True
            if self.journal_id.type == 'purchase' and self.journal_id.use_documents:
                conf = self.env['ir.config_parameter']
                c_value = conf.get_param('check.citi_pl_box')
                if c_value == "True":
                    doit = True
            if doit:
                raise ValidationError(_('la factura debe tener fecha de vencimiento'))

    @api.constrains('payment_term_id')
    def on_save_payment_term_id(self):
        if not self.payment_term_id:
            if self.journal_id.type == 'sale' and self.journal_id.use_documents:
                conf = self.env['ir.config_parameter']
                c_value = conf.get_param('check.citi_sl_box')
                if self.type in ['out_invoice','out_refund'] and c_value == "True":
                    raise ValidationError(_('la factura debe tener termino de pago'))

    @api.model
    def _prepare_refund(self, invoice, date_invoice=None, date=None, description=None, journal_id=None):
        values = super(AccountInvoice, self)._prepare_refund(invoice, date_invoice, date, description, journal_id)
        if self.journal_id.type == 'sale' and self.journal_id.use_documents:
            conf = self.env['ir.config_parameter']
            c_value = conf.get_param('check.citi_sl_box')
            if self.type in ['out_invoice', 'out_refund'] and c_value == "True":
                values['payment_term_id'] = self.env['account.payment.term'].search([],limit=1).id
        return values


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    @api.onchange('name','product_id','invoice_line_tax_ids','purchase_id','quantity','price_unit','discount','price_subtotal')
    def onchange_name_line(self):
        if not self.product_id:
            doit = False
            if self.invoice_id.journal_id.type == 'sale' and self.invoice_id.journal_id.use_documents:
                conf = self.env['ir.config_parameter']
                c_value = conf.get_param('check.citi_sl_box')
                if c_value == "True":
                    doit = True
            if self.invoice_id.journal_id.type == 'purchase' and self.invoice_id.journal_id.use_documents:
                conf = self.env['ir.config_parameter']
                c_value = conf.get_param('check.citi_pl_box')
                if c_value == "True":
                    doit = True

            if doit:
                self.invoice_line_tax_ids = False
                self.purchase_id = False
                self.quantity = 0
                self.price_unit = 0
                self.discount = 0
                self.price_subtotal = 0

    @api.constrains('product_id','invoice_line_tax_ids')
    def on_save_invoice_line_ids(self):
        if self.product_id and not self.invoice_line_tax_ids:
            doit = False
            if self.invoice_id.journal_id.type == 'sale' and self.invoice_id.journal_id.use_documents:
                conf = self.env['ir.config_parameter']
                c_value = conf.get_param('check.citi_sl_box')
                if c_value == "True":
                    doit = True
            if self.invoice_id.journal_id.type == 'purchase' and self.invoice_id.journal_id.use_documents:
                conf = self.env['ir.config_parameter']
                c_value = conf.get_param('check.citi_pl_box')
                if c_value == "True":
                    doit = True

            if doit:
                raise ValidationError(_('la factura debe tener al menos un impuesto por linea'))

    @api.multi
    def write(self, vals):
        for rec in self:
            if not rec.product_id:
                doit = False
                if rec.invoice_id.journal_id.type == 'sale' and rec.invoice_id.journal_id.use_documents:
                    conf = self.env['ir.config_parameter']
                    c_value = conf.get_param('check.citi_sl_box')
                    if c_value == "True":
                        doit = True
                if rec.invoice_id.journal_id.type == 'purchase' and rec.invoice_id.journal_id.use_documents:
                    conf = self.env['ir.config_parameter']
                    c_value = conf.get_param('check.citi_pl_box')
                    if c_value == "True":
                        doit = True
                if doit:
                    #vals['account_id'] = False
                    vals['invoice_line_tax_ids'] = False
                    vals['purchase_id'] = False
                    vals['quantity'] = 0
                    vals['price_unit'] = 0
                    vals['discount'] = 0
                    vals['price_subtotal'] = 0
        return super(AccountInvoiceLine, self).write(vals)

