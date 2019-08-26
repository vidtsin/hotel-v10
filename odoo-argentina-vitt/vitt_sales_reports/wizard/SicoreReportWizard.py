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
import re
import unicodedata

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    printable = set(string.printable)
    res =  u"".join([c for c in nfkd_form if not unicodedata.combining(c)])[:30]
    return filter(lambda x: x in printable, res)

class inventory_excel_extended(models.TransientModel):
    _name= "sicore.extended"
    excel_file = fields.Binary('Download TXT')
    file_name = fields.Char('TXT File', size=64)
    excel_file2 = fields.Binary('Download TXT')
    file_name2 = fields.Char('TXT File', size=64)

class sire_report(models.TransientModel):
    _name = 'vitt_sales_reports.reportsicore'

    wh_code = fields.Many2many('account.tax', 'pre_prop_rel', 'sicore_tax_code_id', 'wh_code_id',
                                string='Cod Retencion',
                                ondelete='cascade',
                                domain="[('sicore_tax_code', '!=', False)]")
    date_from = fields.Date(string='Date From', required=True,
        default=datetime.now().strftime('%Y-%m-01'))
    date_to = fields.Date(string='Date To', required=True,
        default=str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])

    def _get_paym_amount(self,paym):
        matched_amount = 0.0
        for line in paym.payment_group_id.matched_move_line_ids:
            if paym.vendorbill.id == line.invoice_id.id:
                payment_group_id = self._context.get('payment_group_id')
                if not payment_group_id:
                    payments = paym.payment_group_id.payment_ids
                    payment_move_lines = payments.mapped('move_line_ids')
                    payment_partial_lines = self.env['account.partial.reconcile'].search(
                        ['|',('credit_move_id', 'in', payment_move_lines.ids),('debit_move_id', 'in', payment_move_lines.ids),
                        ])
                    for rec in line:
                        for pl in (rec.matched_debit_ids + rec.matched_credit_ids):
                            if pl in payment_partial_lines:
                                matched_amount += pl.amount
        return matched_amount

    def sicore_to_txt(self):
        context = self._context
        filename= 'SICORE_SUJETOS.txt'
        filename2= 'SICORE_RETENCIONES.txt'

        #data
        whcode = list(self.wh_code._ids)
        domain = [
            ('payment_date', '>=', self.date_from), ('payment_date', '<=', self.date_to), ('state', 'not in', ['draft','cancel'])
        ]

        invoiceModel = self.env['account.payment']
        payments = invoiceModel.search(domain,order="payment_date")

        tstr = ''
        tstr2 = ''
        for pay in payments:
            if pay.tax_withholding_id:
                if (pay.tax_withholding_id.id in whcode) or (whcode == []):
                    tstr += "{:<11}".format(pay.partner_id.main_id_number)


                    if pay.partner_id.name:
                        tmpstr = remove_accents(pay.partner_id.name[0:20])
                    else:
                        tmpstr = ""

                    tstr += "{:<20}".format(tmpstr)
                    street = ""
                    if pay.partner_id.street:
                        street = pay.partner_id.street
                    if pay.partner_id.street2:
                        street += pay.partner_id.street2

                    if street:
                        tmpstr = remove_accents(street[0:20])
                    else:
                        tmpstr = ""

                    tstr += "{:<20}".format(tmpstr)
                    tmp = pay.partner_id.city

                    if tmp:
                        tmpstr = remove_accents(tmp[0:20])
                    else:
                        tmpstr = ""

                    tstr += "{:<20}".format(tmpstr)
                    tstr += "{:0>2}".format(pay.partner_id.state_id.afip_code)
                    tstr += "{:<8}".format(pay.partner_id.zip)
                    tstr += "{:0>2}".format(pay.partner_id.main_id_category_id.afip_code)

                    tstr += '\r\n'

        for pay in payments:
            if pay.tax_withholding_id:
                if ((pay.tax_withholding_id.id in whcode) or (whcode == [])) and (pay.partner_id.supplier == True) and \
                (pay.payment_group_id.retencion_ganancias != 'no_aplica'):
                    tstr2 += "{:0<2}".format('06')
                    tstr2 += pay.payment_date[8:10] + '/' + pay.payment_date[5:7] + '/' + pay.payment_date[0:4]
                    tstr2 += "{:<16}".format(pay.display_name)
                    tstr2 += "{:0>16.2f}".format(float(self._get_paym_amount(pay)))
                    tstr2 += "{:0>3}".format(pay.sicore_tax_code)
                    tstr2 += "{:0>3}".format(pay.regcode)
                    whtype = pay.payment_group_id.retencion_ganancias
                    if whtype == 'nro_regimen':
                        tstr2 += "{:0>1}".format('1')
                    elif whtype == 'imposibilidad_retencion':
                        tstr2 += "{:0>1}".format('4')
                    else:
                        tstr2 += "{:0>1}".format('?')

                    if pay.withholdable_invoiced_amount2 > 0:
                        tstr2 += "{:0>14.2f}".format(pay.withholdable_invoiced_amount2)
                    else:
                        tstr2 += "{:0>14.2f}".format(pay.withholdable_invoiced_amount)
                    tstr2 += pay.payment_date[8:10] + '/' + pay.payment_date[5:7] + '/' + pay.payment_date[0:4]
                    tstr2 += "{:0>2}".format(pay.partner_id.afip_responsability_type_id.code)
                    tstr2 += "{:0>1}".format('0')
                    tstr2 += "{:0>14.2f}".format(pay.amount)
                    tstr2 += "{:0>6}".format('0')
                    tstr2 += pay.payment_date[8:10] + '/' + pay.payment_date[5:7] + '/' + pay.payment_date[0:4]
                    if pay.partner_id.main_id_category_id.afip_code in [80, 86, 83, 87, 84]:
                        tstr2 += "{:0>2}".format(pay.partner_id.main_id_category_id.afip_code)
                    else:
                        tstr2 += "{:0>2}".format('??')
                    tmpstr = pay.partner_id.main_id_number
                    tstr2 += "{:0>20}".format(tmpstr.replace('-', '0'))
                    tmpstr = re.sub("\D", "", pay.withholding_number)
                    if not pay.withholding_number:
                        tmpstr = '??????????????'
                    tstr2 += "{:0>14}".format(tmpstr.replace('-', '0'))
                    if pay.partner_id.main_id_category_id.afip_code in [83, 84] and pay.partner_id.state_id.afip_code == '99':

                        tmpstr = remove_accents(pay.partner_id.name[0:30])

                        tstr2 += "{:>30}".format(tmpstr)
                        tstr2 += "{:0>1}".format('0')
                        tstr2 += "{:0>11}".format(pay.partner_id.Country.cuit_juridica[0:11])
                        tstr2 += "{:0>11}".format(pay.partner_id.main_id_number[0:11])
                    else:
                        tstr2 += "{:>30}".format(' ')
                        tstr2 += "{:0>1}".format('0')
                        tstr2 += "{:0>11}".format('0')
                        tstr2 += "{:0>11}".format('0')
                    tstr2 += '\r\n'

        fp = StringIO()
        fp2 = StringIO()
        fp.write(tstr)
        fp2.write(tstr2)
        export_id = self.env['sicore.extended'].create({'excel_file': base64.encodestring(fp.getvalue()), 'file_name': filename,
                                                        'excel_file2': base64.encodestring(fp2.getvalue()),'file_name2': filename2}).id
        fp.close()
        fp2.close()
        return{
            'view_mode': 'form',
            'res_id': export_id,
            'res_model': 'sicore.extended',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'context': context,
            'target': 'new',
        }

