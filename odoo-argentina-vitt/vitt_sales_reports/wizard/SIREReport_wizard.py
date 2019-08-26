from datetime import datetime
from dateutil import relativedelta
from odoo import http, models, fields, api, _
from cStringIO import StringIO
import base64
from odoo import conf
import imp
from decimal import *

TWOPLACES = Decimal(10) ** -2

class inventory_excel_extended(models.TransientModel):
    _name= "sire.extended"
    excel_file = fields.Binary('Download TXT')
    file_name = fields.Char('TXT File', size=64)


class sire_report(models.TransientModel):
    _name = 'vitt_sales_reports.reportsire'

    vepaym = fields.Boolean(string="Incluir Pago a Proveedores",default=True)
    cupaym = fields.Boolean(string="Incluir Recibos a Clientes",default=True)
    wh_id = fields.Many2one('account.tax','Cod Retencion',
                                 ondelete='cascade',
                                 domain="[('withholding_type','!=','none')]")
    date_from = fields.Date(string='Date From', required=True,
        default=datetime.now().strftime('%Y-%m-01'))
    date_to = fields.Date(string='Date To', required=True,
        default=str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])


    def sire_to_txt(self):
        context = self._context
        filename= 'SIRE.txt'

        #data
        whcode = self.wh_id
        domain = [
            ('payment_date', '>=', self.date_from), ('payment_date', '<=', self.date_to), ('state', 'not in', ['draft','cancel'])
        ]

        invoiceModel = self.env['account.payment']
        payments = invoiceModel.search(domain,order="payment_date")

        tstr = ''
        for pay in payments:
            if pay.journal_id.use_documents:
                found = False
                if self.cupaym and pay.partner_type == 'customer':
                    found = True
                if self.vepaym and pay.partner_type == 'supplier':
                    found = True
                if whcode and found:
                    if pay.tax_withholding_id.id != whcode.id:
                        found = False
                if found and not pay.vendorbill:
                    found = False

                if found:
                    tstr += "{:0>4}".format('2004')
                    tstr += "{:0>4}".format('0100')
                    tstr += "{:0>10}".format('0')
                    tstr += "{:0>11}".format(pay.company_id.main_id_number)
                    tstr += "{:0>3}".format('353')
                    tstr += "{:0>3}".format(pay.tax_withholding_id.regcode)
                    tstr += "{:0>11}".format(pay.partner_id.main_id_number)
                    tstr += pay.payment_date[8:10] + '/' + pay.payment_date[5:7] + '/' + pay.payment_date[0:4]
                    if pay.vendorbill:
                        if pay.vendorbill.journal_document_type_id.document_type_id.internal_type == 'credit_note':
                            tstr += "{:0>2}".format('3')
                        else:
                            tstr += "{:0>2}".format('1')
                        tstr += pay.vendorbill.date_invoice[8:10] + '/' + pay.vendorbill.date_invoice[5:7] + '/' + pay.vendorbill.date_invoice[0:4]
                        tstr += "{:0>4}".format(pay.vendorbill.document_number[0:4]) + '-' + "{:0>11}".format(pay.vendorbill.document_number[6:])
                    else:
                        tstr += "{:0>2}".format('2')
                        tstr += pay.payment_date[8:10] + '/' + pay.payment_date[5:7] + '/' + pay.payment_date[0:4]
                        tstr += "{:>16}".format(pay.display_name)
                    tstr += "{:0>14.2f}".format(pay.withholding_base_amount)
                    tstr += "{:0>14.2f}".format(pay.amount)
                    tstr += "{:0>25}".format(pay.withholding_number)
                    tstr += pay.payment_date[8:10] + '/' + pay.payment_date[5:7] + '/' + pay.payment_date[0:4]
                    tstr += "{:0>14.2f}".format(pay.amount)
                    tstr += "{:>30}".format(' ')

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

