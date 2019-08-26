from datetime import datetime
from dateutil import relativedelta
from odoo import http, models, fields, api, _
import xlwt
from cStringIO import StringIO
import base64
from odoo import conf
import imp
from decimal import *
import copy
from collections import OrderedDict
import unicodedata
import string

TWOPLACES = Decimal(10) ** -2

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    printable = set(string.printable)
    res =  u"".join([c for c in nfkd_form if not unicodedata.combining(c)])[:30]
    return filter(lambda x: x in printable, res)

class AccountTax(models.Model):
    _inherit = "account.tax"

    vatreport_included = fields.Boolean(string="Incluir en Libros Iva",translate=True)

def MultiplybyRate(rate, amountincur, curcomp, invcur):
    if curcomp != invcur:
        return rate * amountincur
    else:
        return amountincur

class inventory_excel_extended(models.TransientModel):
    _name= "excel.extended"
    excel_file = fields.Binary('Download report Excel')
    file_name = fields.Char('Excel File', size=64)


class sales_reports(models.TransientModel):
    _name = 'vitt_sales_reports.reportvat'

    vatcode_id = fields.Many2one('account.tax','Cod IVA',
                                 ondelete='cascade',
                                 domain="[('type_tax_use','=','sale')]")
    date_from = fields.Date(string='Date From', required=True,
        default=datetime.now().strftime('%Y-%m-01'))
    date_to = fields.Date(string='Date To', required=True,
        default=str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])
    det_level = fields.Selection(
        [('detailed','Detallado'),
        ('overview','Resumido')],
        'Nivel de Detalle',
        default='detailed',
        translate=True,
    )
    journal_ids = fields.Many2many('account.journal',
                                 string="Journal",
                                 Translate=True,
                                 domain=[('type', '=', 'sale'),('use_documents', '=', True)]
                                 )

    def gettotalsperVAT(self,invoices=None):

        arrayvat = OrderedDict()
        arrayvat['IVA 21%'] = 0.00
        arrayvat['IVA 10.50%'] = 0.00
        arrayvat['IVA 27%'] = 0.00
        arrayvat['IVA 5%'] = 0.00
        arrayvat['IVA 2.50%'] = 0.00
        for inv in invoices:
            if inv.journal_id.use_documents:
                totval4 = 0.00
                totval5 = 0.00
                totval6 = 0.00
                totval8 = 0.00
                totval9 = 0.00

                totval4 = sum(inv.tax_line_ids.filtered(lambda r: (
                    r.tax_id.tax_group_id.type == 'tax' and
                    r.tax_id.tax_group_id.tax == 'vat') and
                    r.tax_id.tax_group_id.afip_code == 4 and
                    r.tax_id.vatreport_included == True).mapped('amount'))
                if totval4 > 0:
                    total = float(MultiplybyRate(inv.currency_rate, totval4, inv.company_currency_id, inv.currency_id))
                    if inv.document_type_id.internal_type == 'credit_note':
                        total *= -1
                    arrayvat['IVA 10.50%'] += total

                totval5 = sum(inv.tax_line_ids.filtered(lambda r: (
                    r.tax_id.tax_group_id.type == 'tax' and
                    r.tax_id.tax_group_id.tax == 'vat') and
                    r.tax_id.tax_group_id.afip_code == 5 and
                    r.tax_id.vatreport_included == True).mapped('amount'))
                if totval5 > 0:
                    total = float(MultiplybyRate(inv.currency_rate, totval5, inv.company_currency_id, inv.currency_id))
                    if inv.document_type_id.internal_type == 'credit_note':
                        total *= -1
                    arrayvat['IVA 21%'] += total

                totval6 = sum(inv.tax_line_ids.filtered(lambda r: (
                    r.tax_id.tax_group_id.type == 'tax' and
                    r.tax_id.tax_group_id.tax == 'vat') and
                    r.tax_id.tax_group_id.afip_code == 6 and
                    r.tax_id.vatreport_included == True).mapped('amount'))
                if totval6 > 0:
                    total = float(MultiplybyRate(inv.currency_rate, totval6, inv.company_currency_id, inv.currency_id))
                    if inv.document_type_id.internal_type == 'credit_note':
                        total *= -1
                    arrayvat['IVA 27%'] += total

                totval8 = sum(inv.tax_line_ids.filtered(lambda r: (
                    r.tax_id.tax_group_id.type == 'tax' and
                    r.tax_id.tax_group_id.tax == 'vat') and
                    r.tax_id.tax_group_id.afip_code == 8 and
                    r.tax_id.vatreport_included == True).mapped('amount'))
                if totval8 > 0:
                    total = float(MultiplybyRate(inv.currency_rate, totval8, inv.company_currency_id, inv.currency_id))
                    if inv.document_type_id.internal_type == 'credit_note':
                        total *= -1
                    arrayvat['IVA 5%'] += total

                totval9 = sum(inv.tax_line_ids.filtered(lambda r: (
                    r.tax_id.tax_group_id.type == 'tax' and
                    r.tax_id.tax_group_id.tax == 'vat') and
                    r.tax_id.tax_group_id.afip_code == 9 and
                    r.tax_id.vatreport_included == True).mapped('amount'))
                if totval9 > 0:
                    total = float(MultiplybyRate(inv.currency_rate, totval9, inv.company_currency_id, inv.currency_id))
                    if inv.document_type_id.internal_type == 'credit_note':
                        total *= -1
                    arrayvat['IVA 2.50%'] += total
        return arrayvat

    def get_new_array(self):
        # 1-  'IVA 10.50%' = 4
        # 2-  'IVA 21%'    = 5
        # 3-  'IVA 27%'    = 6
        # 4-  'IVA 5%'     = 8
        # 5-  'IVA 2.50%'  = 9
        # 6-  'exempt'     = 2
        # 7-  'novat'      = 1
        # 8-  'nett' = [3,4,5,6,8,9]
        # 9-  'perception' => type = 'perception' & tax = 'vat'
        # 10- 'grossincome' => type = 'perception' & tax = 'gross_income'

        # id's of vats
        s1 = self.env['account.tax'].search([('tax_group_id.type', '=', 'tax'),('tax_group_id.tax', '=', 'vat'),('tax_group_id.afip_code', '=', 4),('vatreport_included', '=', True)]).ids
        s2 = self.env['account.tax'].search([('tax_group_id.type', '=', 'tax'),('tax_group_id.tax', '=', 'vat'),('tax_group_id.afip_code', '=', 5),('vatreport_included', '=', True)]).ids
        s3 = self.env['account.tax'].search([('tax_group_id.type', '=', 'tax'),('tax_group_id.tax', '=', 'vat'),('tax_group_id.afip_code', '=', 6),('vatreport_included', '=', True)]).ids
        s4 = self.env['account.tax'].search([('tax_group_id.type', '=', 'tax'),('tax_group_id.tax', '=', 'vat'),('tax_group_id.afip_code', '=', 8),('vatreport_included', '=', True)]).ids
        s5 = self.env['account.tax'].search([('tax_group_id.type', '=', 'tax'),('tax_group_id.tax', '=', 'vat'),('tax_group_id.afip_code', '=', 9),('vatreport_included', '=', True)]).ids
        s6 = self.env['account.tax'].search([('tax_group_id.type', '=', 'tax'),('tax_group_id.tax', '=', 'vat'),('tax_group_id.afip_code', '=', 2),('vatreport_included', '=', True)]).ids
        s7 = self.env['account.tax'].search([('tax_group_id.type', '=', 'tax'),('tax_group_id.tax', '=', 'vat'),('tax_group_id.afip_code', '=', 1),('vatreport_included', '=', True)]).ids
        s8 = self.env['account.tax'].search([('tax_group_id.type', '=', 'tax'),('tax_group_id.tax', '=', 'vat'),('tax_group_id.afip_code', 'in', [3,4,5,6,8,9]),('vatreport_included', '=', True)]).ids
        s9 = self.env['account.tax'].search([('tax_group_id.type', '=', 'perception'),('tax_group_id.tax', '=', 'vat'),('vatreport_included', '=', True)]).ids
        s10 = self.env['account.tax'].search([('tax_group_id.type', '=', 'perception'),('tax_group_id.tax', '=', 'gross_income'),('vatreport_included', '=', True)]).ids
        s11 = self.env['account.tax'].search([('tax_group_id.type', '=', 'tax'),('tax_group_id.tax', '=', 'other'),('tax_group_id.afip_code', '=', 4),('vatreport_included', '=', True)]).ids

        return {'IVA 10.50%':s1,'IVA 21%':s2,'IVA 27%':s3,'IVA 5%':s4,'IVA 2.50%':s5,'exempt':s6,'novat':s7,'nett':s8,'perception':s9,'grossincome':s10,'other':s11}

    def fill_array(self,new_array,invoices):
        new_vat_array = OrderedDict()
        var = total = 0.0
        for inv in invoices:
            new_vat_array[inv.id] = {'IVA 10.50%': 0.0, 'IVA 21%': 0.0, 'IVA 27%': 0.0, 'IVA 5%': 0.0, 'IVA 2.50%': 0.0,
                                     'exempt': 0.0, 'novat': 0.0, 'nett': 0.0, 'perception': 0.0, 'grossincome': 0.0,
                                     'other': 0.0}
            if inv.state != 'cancel':
                for line in inv.tax_line_ids:
                    for tax in new_array:
                        if line.tax_id.id in new_array[tax]:
                            if tax in ['exempt','novat','nett']:
                                var = line.base
                            else:
                                var = line.amount

                            total = float(MultiplybyRate(inv.currency_rate, var, inv.company_currency_id, inv.currency_id))
                            if inv.document_type_id.internal_type == 'credit_note':
                                total *= -1
                            new_vat_array[inv.id][tax] += float(Decimal(total).quantize(TWOPLACES))
        return new_vat_array


    def Print_to_excel(self):
        context = self._context
        filename= 'Libro_IVA_Ventas.xls'
        #filename2= 'Libro_IVA_Ventas2.txt'
        workbook= xlwt.Workbook(encoding="UTF-8")
        worksheet= workbook.add_sheet('Detalle')
        #style = xlwt.easyxf('font:height 400, bold True, name Arial; align: horiz center, vert center;borders: top medium,right medium,bottom medium,left medium')
        #worksheet.write_merge(0,1,0,7,'REPORT IN EXCEL',style)
        
        #data
        vatcode_ids = list(self.vatcode_id)
        date_froms = self.date_from
        date_tos = self.date_to
        domain = [
            ('date', '>=', date_froms), ('date', '<=', date_tos),
            ('type', '!=', 'in_invoice'),('type', '!=', 'in_refund'),
            ('journal_id.use_documents', '=', True),('state', 'not in', ['draft'])
        ]
        if self.journal_ids:
            domain.append(('journal_id.id', 'in', list(self.journal_ids._ids)))

        invoiceModel = self.env['account.invoice']
        invoices = invoiceModel.search(domain,order="date_invoice,display_name2")
        #vatarray = self.gettotalsperVAT(invoices)
        vatarray = {}
        new_array = self.get_new_array()
        new_vat_array = self.fill_array(new_array,invoices)

        # Titles
        worksheet.write(0, 0, _('Nombre del Informe: Libro IVA Ventas'))
        worksheet.write(1, 0, _('Empresa: ') + self.env.user.company_id.name)
        cuit = self.env.user.company_id.partner_id.main_id_number
        worksheet.write(2, 0, _('CUIT: ') + cuit[0:2] + '-' + cuit[2:10] + '-' + cuit[10:11])
        worksheet.write(4, 0, _('Periodo ') +
                        date_froms[8:10] + '-' + date_froms[5:7] + '-' + date_froms[0:4]
                        + ':' + date_tos[8:10] + '-' + date_tos[5:7] + '-' + date_tos[0:4])


        vattot = OrderedDict()
        vattot['IVA 21%'] = 0.00
        vattot['IVA 10.50%'] = 0.00
        vattot['IVA 27%'] = 0.00
        vattot['IVA 5%'] = 0.00
        vattot['IVA 2.50%'] = 0.00

        #columns
        index = 5
        if self.det_level == 'detailed':
            subindex = 0
            worksheet.write(index,subindex,_('Fecha'))
            subindex += 1
            worksheet.write(index,subindex,_('Tipo Doc'))
            subindex += 1
            worksheet.write(index,subindex,_('Letra'))
            subindex += 1
            worksheet.write(index,subindex,_('Nro. Comp'))
            subindex += 1
            worksheet.write(index,subindex,_('Resp IVA'))
            subindex += 1
            worksheet.write(index,subindex,_('CUIT/CUIL'))
            subindex += 1
            worksheet.write(index,subindex,_('Nombre'))
            subindex += 1
            worksheet.write(index,subindex,_('Neto Gravado'))
            subindex += 1
            for key in vattot:
                worksheet.write(index,subindex, key)
                subindex += 1
            worksheet.write(index,subindex,_('Exento'))
            subindex += 1
            worksheet.write(index,subindex,_('Percepcion IVA'))
            subindex += 1
            worksheet.write(index,subindex,_('Percepcion IIBB'))
            subindex += 1
            worksheet.write(index,subindex,_('Impuestos Internos'))
            subindex += 1
            worksheet.write(index,subindex,_('No Gravado'))
            subindex += 1
            #worksheet.write(0,11,'IVA')
            worksheet.write(index,subindex,_('Total'))
        else:
            subindex = 0
            worksheet.write(index,subindex,_('Fecha'))
            subindex += 1
            worksheet.write(index,subindex,_('Nombre'))
            subindex += 1
            worksheet.write(index,subindex,_('CUIT/CUIL'))
            subindex += 1
            worksheet.write(index,subindex,_('Resp IVA'))
            subindex += 1
            worksheet.write(index,subindex,_('Tipo Doc'))
            subindex += 1
            worksheet.write(index,subindex,_('Serie'))
            subindex += 1
            worksheet.write(index,subindex,_('Nro. Comp'))
            subindex += 1
            worksheet.write(index,subindex,_('Total'))
            subindex += 1
            worksheet.write(index,subindex,_('Neto Gravado'))
            subindex += 1
            worksheet.write(index,subindex,_('No Gravado'))
            subindex += 1
            worksheet.write(index,subindex,_('IVA'))
            subindex += 1
            worksheet.write(index,subindex,_('Percepciones'))
            subindex += 1
            worksheet.write(index,subindex,_('Impuestos Internos'))
            subindex += 1

        index = 7
        camount_untaxed = 0
        gettotpercep = 0
        gettotgrossincome  = 0
        gettotexempt = 0
        gettotnovat = 0
        camount_total = 0
        gettotinttaxes = 0
        tot1 = tot2 = tot3 = tot4 = tot5 = tot6 = 0

        matrix = {}
        matrixbase = {}
        vatcodes = {}
        vatcodesbase = {}
        tmp = 0.0
        for o in invoices:
            if o.journal_id.use_documents and o.validated_inv(self):
                subindex = 0
                if o.document_number:
                    if len(o.document_number) == 13:
                        nr_ = "0" + str(o.document_number)
                    else:
                        nr_ = str(o.document_number)
                else:
                    nr_ = ""
                if self.det_level == 'detailed':
                    worksheet.write(index, subindex, o.date_invoice)
                    subindex += 1

                    worksheet.write(index, subindex, o.journal_document_type_id.document_type_id.report_name)
                    subindex += 1


                    let = o.journal_document_type_id.document_type_id.document_letter_id.name
                    worksheet.write(index, subindex, str(let))  # letra
                    subindex += 1

                    worksheet.write(index, subindex, nr_)  # nro comprob
                    subindex += 1

                    worksheet.write(index, subindex,  str(o.partner_id.afip_responsability_type_id.report_code_name))
                    subindex += 1

                    if str(o.partner_id.main_id_number) == 'False':
                        worksheet.write(index, subindex, ' ')
                    else:
                        cuit = o.partner_id.main_id_number
                        if o.partner_id.main_id_category_id.code != 'DNI':
                            worksheet.write(index, subindex,cuit[0:2] + '-' + cuit[2:10] + '-' + cuit[10:11])
                        else:
                            worksheet.write(index, subindex, cuit)
                    subindex += 1

                    if o.state != 'cancel':
                        worksheet.write(index, subindex,  o.partner_id.name)
                    else:
                        worksheet.write(index, subindex, "ANULADA")
                    subindex += 1

                    #tot = o.camount_untaxed()
                    tot = new_vat_array[o.id]['nett']
                    worksheet.write(index, subindex, tot)
                    camount_untaxed += tot
                    subindex += 1

                    #worksheet.write(index, 11, o.gettotvat())
                    #vatarray = self.gettotalsperVAT(o)
                    for key in vattot:
                        worksheet.write(index, subindex, new_vat_array[o.id][key])
                        vattot[key] += new_vat_array[o.id][key]
                        subindex += 1

                    #tot = o.gettotexempt()
                    tot = new_vat_array[o.id]['exempt']
                    worksheet.write(index, subindex, tot)
                    gettotexempt += tot
                    subindex += 1

                    #tot = o.gettotpercep()
                    tot = new_vat_array[o.id]['perception']
                    worksheet.write(index, subindex, tot)
                    gettotpercep += tot
                    subindex += 1

                    #tot = o.gettotgrossincome()
                    tot = new_vat_array[o.id]['grossincome']
                    worksheet.write(index, subindex, tot)
                    gettotgrossincome += tot
                    subindex += 1

                    #tot = o.gettotinttaxes()
                    tot = new_vat_array[o.id]['other']
                    worksheet.write(index, subindex, tot)
                    gettotinttaxes += tot
                    subindex += 1

                    #tot = o.gettotnovat()
                    tot = new_vat_array[o.id]['novat']
                    worksheet.write(index, subindex, tot)
                    gettotnovat += tot
                    subindex += 1

                    if o.state != 'cancel':
                        tot = o.camount_total()
                        worksheet.write(index, subindex, tot)
                        camount_total += tot
                    else:
                        worksheet.write(index, subindex, 0)
                    index += 1

                    #Matrix for vat totals grouped by document_type_id
                    if o.state != 'cancel':
                        for vat in o.tax_line_ids:
                            if vat.tax_id.vatreport_included:
                                amount = float(MultiplybyRate(o.currency_rate, vat.amount, o.company_currency_id, o.currency_id))
                                base = float(MultiplybyRate(o.currency_rate, vat.base, o.company_currency_id, o.currency_id))
                                name_key = o.partner_id.afip_responsability_type_id.name

                                if vat.name in vatcodes:
                                    vatcodes[vat.name] += amount
                                else:
                                    vatcodes.update({vat.name: amount})

                                monto = 0
                                if vat.amount > 0:
                                    if o.document_type_id.internal_type == 'credit_note':
                                        monto = -amount
                                    else:
                                        monto = amount
                                if vat.amount == 0:
                                    if vat.tax_id.tax_group_id.tax != 'gross_income':
                                        if o.document_type_id.internal_type == 'credit_note':
                                            monto = -base
                                        else:
                                            monto = base

                                if not name_key in matrix.keys():
                                    matrix[name_key] = {vat.name:monto}
                                else:
                                    if not vat.name in matrix[name_key].keys():
                                        matrix[name_key].update({vat.name:monto})
                                    else:
                                        matrix[name_key][vat.name] += monto

                                monto = 0
                                if vat.amount > 0:
                                    if o.document_type_id.internal_type == 'credit_note':
                                        monto = -base
                                    else:
                                        monto = base
                                if vat.amount == 0:
                                    if vat.tax_id.tax_group_id.tax != 'gross_income':
                                        if o.document_type_id.internal_type == 'credit_note':
                                            monto = -amount
                                        else:
                                            monto = amount

                                if not name_key in matrixbase.keys():
                                    matrixbase[name_key] = {vat.name:monto}
                                else:
                                    if not vat.name in matrixbase[name_key].keys():
                                        matrixbase[name_key].update({vat.name:monto})
                                    else:
                                        matrixbase[name_key][vat.name] += monto

                else:
                    worksheet.write(index, subindex, o.date_invoice)
                    subindex += 1

                    worksheet.write(index, subindex, o.partner_id.name)
                    subindex += 1

                    if str(o.partner_id.main_id_number) == 'False':
                        worksheet.write(index, subindex, ' ')
                    else:
                        worksheet.write(index, subindex, o.partner_id.main_id_number)
                    subindex += 1

                    worksheet.write(index, subindex, str(o.partner_id.afip_responsability_type_id.report_code_name))
                    subindex += 1

                    worksheet.write(index, subindex, o.journal_document_type_id.document_type_id.report_name)
                    subindex += 1

                    let = o.journal_document_type_id.document_type_id.document_letter_id.name
                    worksheet.write(index, subindex, str(let))  # letra
                    subindex += 1

                    worksheet.write(index, subindex, nr_)  # nro comprob
                    subindex += 1

                    tot = 0.0
                    if o.document_type_id.internal_type == 'credit_note':
                        tot = -o.camount_total()
                    else:
                        tot = o.camount_total()
                    tot1 += tot
                    worksheet.write(index, subindex, str(tot))
                    subindex += 1

                    worksheet.write(index, subindex, str(new_vat_array[o.id]['nett']))
                    tot2 += o.camount_untaxed()
                    subindex += 1

                    worksheet.write(index, subindex, str(new_vat_array[o.id]['exempt'] + new_vat_array[o.id]['novat']))
                    tot3 += new_vat_array[o.id]['exempt'] + new_vat_array[o.id]['novat']
                    subindex += 1

                    tot = 0.0
                    #vatarray = self.gettotalsperVAT(o)
                    for key in vattot:
                        tot += new_vat_array[o.id][key]
                    tot4 += tot
                    worksheet.write(index, subindex, str(tot))
                    subindex += 1

                    tot = new_vat_array[o.id]['perception'] + new_vat_array[o.id]['grossincome']
                    tot5 += tot
                    worksheet.write(index, subindex, tot)
                    subindex += 1

                    tot = new_vat_array[o.id]['other']
                    tot6 += tot
                    worksheet.write(index, subindex, tot)
                    subindex += 1
                    index += 1

        if self.det_level == 'detailed':
            worksheet.write(index, 0, _("Totales"))
            subindex = 7
            worksheet.write(index, subindex, camount_untaxed)
            subindex += 1
            for key in vattot:
                worksheet.write(index, subindex, vattot[key])
                subindex += 1
            worksheet.write(index, subindex, gettotexempt)
            subindex += 1
            worksheet.write(index, subindex, gettotpercep)
            subindex += 1
            worksheet.write(index, subindex, gettotgrossincome)
            subindex += 1
            worksheet.write(index, subindex, gettotinttaxes)
            subindex += 1
            worksheet.write(index, subindex, gettotnovat)
            subindex += 1
            worksheet.write(index, subindex, camount_total)

            index += 2
            subindex = 0
            if_base = dict()
            worksheet.write(index, subindex, _("Totales Agrupados"))
            subindex += 1
            for code in vatcodes:
                foundf = False
                for type in matrix:
                    for key, value in matrix[type].iteritems():
                        if key == code:
                            if matrixbase[type][key] > 0:
                                foundf = True
                                if_base[key] = True
                if foundf:
                    worksheet.write(index, subindex, _("Base"))
                    subindex += 1
                worksheet.write(index, subindex, code)
                subindex += 1


            # print matrix
            totgrp = 0
            for type in matrix:
                index += 1
                subindex = 0
                worksheet.write(index, subindex, type)
                subindex += 1
                for code in vatcodes:
                    foundf = False
                    for key, value in matrix[type].iteritems():
                        if key == code:
                            foundf = True
                            if key in if_base.keys() and if_base[key] == True:
                                worksheet.write(index, subindex, matrixbase[type][key])
                                subindex += 1
                            worksheet.write(index, subindex, value)
                            subindex += 1
                            totgrp +=  (matrixbase[type][key] + value)
                    if not foundf:
                        subindex += 1
                        if code in if_base.keys() and if_base[code] == True:
                            subindex += 1
                worksheet.write(index, subindex, totgrp)
                subindex += 1
                totgrp = 0

            # index += 2
            # subindex = 0
            # worksheet.write(index, subindex, _("Totales Agrupados"))
            # subindex += 1
            # for code in vatcodes:
            #     worksheet.write(index, subindex, _("Base"))
            #     subindex += 1
            #     worksheet.write(index, subindex, code)
            #     subindex += 1
            # worksheet.write(index, subindex, _("Totales"))
            # subindex += 1
            #
            # # print matrix
            # totgrp = 0
            # for type in matrix:
            #     index += 1
            #     subindex = 0
            #     worksheet.write(index, subindex, type)
            #     subindex += 1
            #     for code in vatcodes:
            #         foundf = False
            #         for key, value in matrix[type].iteritems():
            #             if key == code:
            #                 foundf = True
            #                 worksheet.write(index, subindex, matrixbase[type][key])
            #                 subindex += 1
            #                 worksheet.write(index, subindex, value)
            #                 subindex += 1
            #                 totgrp +=  (matrixbase[type][key] + value)
            #         if not foundf:
            #             subindex += 2
            #     worksheet.write(index, subindex, totgrp)
            #     subindex += 1
            #     totgrp = 0

        else:
            subindex = 7
            worksheet.write(index, subindex, tot1)
            subindex += 1
            worksheet.write(index, subindex, tot2)
            subindex += 1
            worksheet.write(index, subindex, tot3)
            subindex += 1
            worksheet.write(index, subindex, tot4)
            subindex += 1
            worksheet.write(index, subindex, tot5)
            subindex += 1
            worksheet.write(index, subindex, tot6)
            subindex += 1



        fp = StringIO()
        workbook.save(fp)
        export_id = self.env['excel.extended'].create({'excel_file': base64.encodestring(fp.getvalue()), 'file_name': filename }).id
        fp.close()
        return{
            'view_mode': 'form',
            'res_id': export_id,
            'res_model': 'excel.extended',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'context': context,
            'target': 'new',
        }


    @api.multi
    def ex_salesvatreport(self):
        datas = {
          'filter': self.vatcode_id.id,
          'date_froms': self.date_from,
          'date_tos': self.date_to,
          'journal_ids': list(self.journal_ids._ids),
        }
        return self.env['report'].with_context(landscape=True).get_action(self, 'vitt_sales_reports.reportvat', data=datas)


class report_vitt_sales_reports_reportvat(models.Model):
    _name = "report.vitt_sales_reports.reportvat"

    def render_html(self,docids, data=None):
        domain = [
            ('date', '>=', data['date_froms']), ('date', '<=', data['date_tos']),
            ('type', '!=', 'in_invoice'),('type', '!=', 'in_refund'),
            ('journal_id.use_documents', '=', True),('state', 'not in', ['draft','cancel']),
            ('journal_id.id', 'in', data['journal_ids'])
        ]
        invoiceModel = self.env['account.invoice']
        invoices = invoiceModel.search(domain,order="date_invoice")
        report_obj = self.env['report']
        report = report_obj._get_report_from_name('vitt_sales_reports.reportvat')
        docargs = {
            'doc_ids': invoices._ids,
            'doc_model': report.model,
            'docs': invoices,
        }
        return self.env['report'].render('vitt_sales_reports.reportvat', docargs)


class def_sales_reports_reportvat(models.Model):
    _inherit = "account.invoice"

    def validated_inv(self, wizard):
        return True

    @api.multi
    def camount_untaxed(self,invoice=None):
        if invoice != None:
            self = invoice
        self.ensure_one()
        totval = sum(self.tax_line_ids.filtered(lambda r: (
            r.tax_id.tax_group_id.type == 'tax' and
            r.tax_id.tax_group_id.tax == 'vat') and
            r.tax_id.tax_group_id.afip_code in [3,4,5,6,8,9] and
            r.tax_id.vatreport_included == True).mapped('base'))
        total = float(MultiplybyRate(self.currency_rate,totval,self.company_currency_id,self.currency_id))
        if self.document_type_id.internal_type == 'credit_note':
            total *= -1
        return Decimal(total).quantize(TWOPLACES)

    @api.multi
    def camount_total(self,invoice=None):
        if invoice != None:
            self = invoice
        self.ensure_one()
        total = float(MultiplybyRate(self.currency_rate,self.amount_total,self.company_currency_id,self.currency_id))
        if self.document_type_id.internal_type == 'credit_note':
            total *= -1
        return Decimal(total).quantize(TWOPLACES)

    @api.multi
    def gettotpercep(self,invoice=None):
        if invoice != None:
            self = invoice
        self.ensure_one()
        totval = sum(self.tax_line_ids.filtered(lambda r: (
            r.tax_id.tax_group_id.type == 'perception' and
            r.tax_id.tax_group_id.tax == 'vat' and
            r.tax_id.vatreport_included == True)).mapped('amount'))
        total = float(MultiplybyRate(self.currency_rate, totval,self.company_currency_id,self.currency_id))
        if self.document_type_id.internal_type == 'credit_note':
            total *= -1
        return Decimal(total).quantize(TWOPLACES)

    @api.multi
    def gettotgrossincome(self,invoice=None):
        if invoice != None:
            self = invoice
        self.ensure_one()
        totval = sum(self.tax_line_ids.filtered(lambda r: (
            r.tax_id.tax_group_id.type == 'perception' and
            r.tax_id.tax_group_id.tax == 'gross_income' and
            r.tax_id.vatreport_included == True)).mapped('amount'))
        total = float(MultiplybyRate(self.currency_rate, totval,self.company_currency_id,self.currency_id))
        if self.document_type_id.internal_type == 'credit_note':
            total *= -1
        return Decimal(total).quantize(TWOPLACES)

    @api.multi
    def gettotexempt(self,invoice=None):
        if invoice != None:
            self = invoice
        self.ensure_one()
        totval = sum(self.tax_line_ids.filtered(lambda r: (
            r.tax_id.tax_group_id.type == 'tax' and
            r.tax_id.tax_group_id.tax == 'vat' and
            r.tax_id.tax_group_id.afip_code == 2 and
            r.tax_id.vatreport_included == True)).mapped('base'))
        total = float(MultiplybyRate(self.currency_rate, totval,self.company_currency_id,self.currency_id))
        if self.document_type_id.internal_type == 'credit_note':
            total *= -1
        return Decimal(total).quantize(TWOPLACES)

    def gettotinttaxes(self,invoice=None):
        if invoice != None:
            self = invoice
        self.ensure_one()
        totval = sum(self.tax_line_ids.filtered(lambda r: (
            r.tax_id.tax_group_id.type == 'tax' and
            r.tax_id.tax_group_id.tax == 'other' and
            r.tax_id.tax_group_id.afip_code == 4) and
            r.tax_id.vatreport_included == True).mapped('amount'))
        total = float(MultiplybyRate(self.currency_rate, totval,self.company_currency_id,self.currency_id))
        if self.document_type_id.internal_type == 'credit_note':
            total *= -1
        return Decimal(total).quantize(TWOPLACES)

    @api.multi
    def gettotnovat(self,invoice=None):
        if invoice != None:
            self = invoice
        self.ensure_one()
        totval = sum(self.tax_line_ids.filtered(lambda r: (
            r.tax_id.tax_group_id.type == 'tax' and
            r.tax_id.tax_group_id.tax == 'vat' and
            r.tax_id.tax_group_id.afip_code == 1 and
            r.tax_id.vatreport_included == True)).mapped('base'))
        total = float(MultiplybyRate(self.currency_rate, totval,self.company_currency_id,self.currency_id))
        if self.document_type_id.internal_type == 'credit_note':
            total *= -1
        return Decimal(total).quantize(TWOPLACES)

    @api.multi
    def gettotvat(self,invoice=None):
        if invoice != None:
            self = invoice
        self.ensure_one()
        totval = sum(self.tax_line_ids.filtered(lambda r: (
            r.tax_id.tax_group_id.type == 'tax' and
            r.tax_id.tax_group_id.tax == 'vat') and
            (r.tax_id.tax_group_id.afip_code in [4,5,6,8,9] and
            r.tax_id.vatreport_included == True)).mapped('amount'))
        total = float(MultiplybyRate(self.currency_rate, totval,self.company_currency_id,self.currency_id))
        if self.document_type_id.internal_type == 'credit_note':
            total *= -1
        return Decimal(total).quantize(TWOPLACES)

    @api.multi
    def getgrandtotals(self,data='',docs={}):
        totval = 0
        total = 0
        for invoice in docs:
            if data=='gettotvat':
                totval = self.gettotvat(invoice)
            if data=='gettotnovat':
                totval = self.gettotnovat(invoice)
            if data=='gettotexempt':
                totval = self.gettotexempt(invoice)
            if data=='gettotgrossincome':
                totval = self.gettotgrossincome(invoice)
            if data=='gettotpercep':
                totval = self.gettotpercep(invoice)
            if data=='camount_total':
                totval = self.camount_total(invoice)
            if data=='camount_untaxed':
                totval = self.camount_untaxed(invoice)
            if data=='gettotinttaxes':
                totval = self.gettotinttaxes(invoice)
            total += totval
        total = float(MultiplybyRate(self.currency_rate, total, self.company_currency_id, self.currency_id))
        if self.document_type_id.internal_type == 'credit_note':
            total *= -1
        return Decimal(total).quantize(TWOPLACES)

