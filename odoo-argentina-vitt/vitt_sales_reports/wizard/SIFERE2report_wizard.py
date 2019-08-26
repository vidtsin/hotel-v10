# -*- coding: utf-8 -*-
from datetime import datetime
from dateutil import relativedelta
from odoo import http, models, fields, api, _
from cStringIO import StringIO
import base64
from odoo import conf
import imp
from decimal import *

TWOPLACES = Decimal(10) ** -2

class sire_report(models.TransientModel):
    _name = 'vitt_sales_reports.reportsifere.vtas'

    date_from = fields.Date(string='Date From', required=True,
        default=datetime.now().strftime('%Y-%m-01'))
    date_to = fields.Date(string='Date To', required=True,
        default=str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])
    wh_id = fields.Many2many('account.tax',string="Cod Retencion",domain="[('type_tax_use','=','customer'), ('jurisdiction_code','!=', False)]")
    jurisd_id = fields.Many2one('jurisdiction.codes','Cod de jurisdiccion')


    def sifere_vtas_to_txt(self):
        context = self._context
        filename= 'SIFERE_VTAS.txt'

        #data
        whcode = self.wh_id
        domain = [
            ('payment_date', '>=', self.date_from),
            ('payment_date', '<=', self.date_to),
            ('state', 'not in', ['draft', 'cancel']),
            ('payment_type', '=', 'inbound')
        ]

        invoiceModel = self.env['account.payment']
        payments = invoiceModel.search(domain,order="payment_date")

        sdata = list()
        for pay in payments:
            found = False
            if 'gross_income' == pay.tax_withholding_id.tax_group_id.tax and \
                'withholding' == pay.tax_withholding_id.tax_group_id.type:

                if not self.wh_id and not self.jurisd_id:
                    found = True
                else:
                    if self.wh_id and self.wh_id.id == pay.tax_withholding_id.id:
                        found = True
                    if self.jurisd_id and self.jurisd_id.id == pay.tax_withholding_id.jurisdiction_code.id:
                        found = True
            if found:
                if not pay.tax_withholding_id.jurisdiction_code:
                    sdata.append("falta codigo de jurisdiccion en " + pay.tax_withholding_id.name.encode('ASCII', 'ignore'))
                if not pay.customerbill:
                    sdata.append("falta Factura en recibo " + pay.display_name)
                else:
                    if not pay.customerbill.partner_id.main_id_number:
                        sdata.append("falta Nro CUIT en contacto " + pay.customerbill.partner_id.name.encode('ASCII', 'ignore'))
                    if not pay.customerbill.journal_document_type_id.document_type_id.name:
                        sdata.append("falta letra de factura en journal doc type " + pay.customerbill.journal_document_type_id.document_type_id.name)
                if not pay.payment_date:
                    sdata.append("falta fecha en pago " + pay.display_name)

                if not pay.withholding_number:
                    sdata.append("falta nro de retencion en pago " + pay.display_name)

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

        tstr2 = tstr = ''
        for pay in payments:
            found = False
            if 'gross_income' == pay.tax_withholding_id.tax_group_id.tax and \
                'withholding' == pay.tax_withholding_id.tax_group_id.type:

                if not self.wh_id and not self.jurisd_id:
                    found = True
                else:
                    if self.wh_id and self.wh_id.id == pay.tax_withholding_id.id:
                        found = True
                    if self.jurisd_id and self.jurisd_id.id == pay.tax_withholding_id.jurisdiction_code.id:
                        found = True
            if found:
                tstr += "{:0>3}".format(pay.tax_withholding_id.jurisdiction_code.name)

                tstr += "{:<2}".format(pay.customerbill.partner_id.main_id_number[0:2])
                tstr += '-' + "{:<8}".format(pay.customerbill.partner_id.main_id_number[2:10])
                tstr += '-' + "{:<1}".format(pay.customerbill.partner_id.main_id_number[10:11])

                tstr += pay.payment_date[8:10] + '/' + pay.payment_date[5:7] + '/' + pay.payment_date[0:4]
                #tstr += "{:0>4}".format(pay.withholding_number[0:4])
                #tstr += "{:0>16}".format(pay.withholding_number[5:14])
                tstr += "{:0>20}".format(pay.withholding_number)
                tstr2 = pay.customerbill.journal_document_type_id.document_type_id.internal_type
                if tstr2 == 'invoice':
                    tstr2 = 'F'
                if tstr2 == 'credit_note':
                    tstr2 = 'C'
                if tstr2 == 'debit_note':
                    tstr2 = 'D'
                tstr += "{:<1}".format(tstr2)
                tstr += "{:<1}".format(pay.customerbill.journal_document_type_id.document_type_id.document_letter_id.name)
                nr = pay.customerbill.display_name.split('-')
                tstr += "{:0>4}".format(nr[0][-4:])
                tstr += "{:0>16}".format(nr[1])
                tstr2 = "{:0>11.2f}".format(pay.amount)
                for l in tstr2:
                    if l == '.':
                        tstr  += ','
                    else:
                        tstr += l

                tstr += '\r\n'


        fp = StringIO()
        fp.write(tstr)
        export_id = self.env['sire.extended'].create({'excel_file': base64.encodestring(fp.getvalue()), 'file_name': filename }).id
        fp.close()
        return{
            'view_mode': 'form',
            'res_id': export_id,
            'res_model': 'sire.extended',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'context': context,
            'target': 'new',
        }

