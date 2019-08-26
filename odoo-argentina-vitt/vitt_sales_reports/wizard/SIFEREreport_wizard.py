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

class sifere_report(models.Model):
    _inherit = 'res.country.state'

    afip_code = fields.Char('Codigo SIFERE', size=2)

class sire_report(models.TransientModel):
    _name = 'vitt_sales_reports.reportsifere'

    date_from = fields.Date(string='Date From', required=True,
        default=datetime.now().strftime('%Y-%m-01'))
    date_to = fields.Date(string='Date To', required=True,
        default=str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])
    wh_id = fields.Many2many('account.tax',
                            string="Cod Percepcion",
                            domain="[('type_tax_use','=','purchase'), ('jurisdiction_code','!=', False)]",
                            translate=True
                            )
    jurisd_id = fields.Many2one('jurisdiction.codes','Cod de jurisdiccion')


    def sifere_to_txt(self):
        context = self._context
        filename= 'SIFERE.txt'

        #data
        whcode = self.wh_id
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('state', 'not in', ['draft','cancel']),
        ]

        invoiceModel = self.env['account.invoice']
        invoices = invoiceModel.search(domain,order="date_invoice")

        sdata = list()
        for inv in invoices:
            if inv.journal_id.use_documents:
                for tax in inv.tax_line_ids:
                    if 'gross_income' == tax.tax_id.tax_group_id.tax and \
                            'perception' == tax.tax_id.tax_group_id.type and \
                            'purchase' == tax.tax_id.type_tax_use and \
                            tax.amount > 0:

                        found = False
                        if not self.wh_id and not self.jurisd_id:
                            found = True
                        else:
                            if self.wh_id and tax.tax_id.id in list(self.wh_id._ids):
                                found = True
                            if self.jurisd_id and self.jurisd_id.id == tax.tax_id.jurisdiction_code.id:
                                found = True

                        if found:
                            if not tax.tax_id.jurisdiction_code:
                                sdata.append("falta codigo de jurisdiccion en " + tax.tax_id.name.encode('ASCII', 'ignore'))
                            if not inv.partner_id.main_id_number:
                                sdata.append("falta Nro CUIT en contacto " + inv.partner_id.name.encode('ASCII', 'ignore'))
                            if not inv.date_invoice:
                                sdata.append("falta fecha factura en factura " + inv.display_name)
                            if not inv.document_number:
                                sdata.append("falta nro de documento en factura " + inv.display_name)
                            if not inv.journal_document_type_id.document_type_id.internal_type:
                                sdata.append("falta tipo de factura en journal doc type " + inv.journal_document_type_id.document_type_id.name.name)
                            if not inv.journal_document_type_id.document_type_id.document_letter_id.name:
                                sdata.append("falta letra de factura en journal doc type " + inv.journal_document_type_id.document_type_id.name.name)

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
        for inv in invoices:
            if inv.journal_id.use_documents:
                for tax in inv.tax_line_ids:
                    found = False
                    if 'gross_income' == tax.tax_id.tax_group_id.tax and \
                        'perception' == tax.tax_id.tax_group_id.type and \
                        'purchase' == tax.tax_id.type_tax_use and \
                        tax.amount > 0:

                        if not self.wh_id and not self.jurisd_id:
                            found = True
                        else:
                            if self.wh_id and tax.tax_id.id in list(self.wh_id._ids):
                                found = True
                            if self.jurisd_id and self.jurisd_id.id == tax.tax_id.jurisdiction_code.id:
                                found = True
                    if found:
                        tstr += "{:0>3}".format(tax.tax_id.jurisdiction_code.name)

                        tstr += "{:<2}".format(inv.partner_id.main_id_number[0:2])
                        tstr += '-' + "{:<8}".format(inv.partner_id.main_id_number[2:10])
                        tstr += '-' + "{:<1}".format(inv.partner_id.main_id_number[10:11])

                        tstr += inv.date_invoice[8:10] + '/' + inv.date_invoice[5:7] + '/' + inv.date_invoice[0:4]
                        nr = inv.document_number.split('-')
                        tstr += "{:0>4}".format(nr[0][-4:])
                        tstr += "{:0>8}".format(nr[1])
                        tstr2 = inv.journal_document_type_id.document_type_id.internal_type
                        if tstr2 == 'invoice':
                            tstr2 = 'F'
                        if tstr2 == 'credit_note':
                            tstr2 = 'C'
                        if tstr2 == 'debit_note':
                            tstr2 = 'D'
                        tstr += "{:<1}".format(tstr2)
                        tstr += "{:<1}".format(inv.journal_document_type_id.document_type_id.document_letter_id.name)
                        tstr2 = "{:0>11.2f}".format(tax.amount)
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

