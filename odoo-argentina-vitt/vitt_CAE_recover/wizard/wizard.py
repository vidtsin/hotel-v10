# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################

from odoo import models, api, fields, _
from odoo.exceptions import UserError
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)

class AccountInvoiceCAERecover(models.TransientModel):
    _name = 'account.invoice.caerecover'

    number = fields.Char(string="Number (EJ: 0021-00010695)", translate=True, size=64)
    doctype_id = fields.Many2one('account.journal.document.type', string="Document Type", translate=True, required=True)
    journal_id = fields.Many2one('account.journal', string="Journal", required=True,domain="[('type', '=', 'sale'),('point_of_sale_type', '=', 'electronic')]")

    def confirm(self):
        ws = self.doctype_id.get_pyafipws_consult_invoice2(self.number)
        if 'factura' not in ws.keys():
            raise UserError(_('No existen datos de esa factura en la Afip'))

        if not ws['factura']['cae'] or not ws['factura']['fch_venc_cae']:
            raise UserError(_('No se pudo retraer CAE'))

        inv = self.env['account.invoice'].search([('afip_auth_code', '=', ws['factura']['cae'])])
        if inv:
            raise UserError(_('you have an invoice with this CAE: %s') % (inv.display_name2))

        active_ids = self._context.get('active_ids', [])
        invoices = self.env['account.invoice'].browse(active_ids)
        foundf = False
        for inv in invoices:
            if inv.type in ['out_invoice','out_refund'] and inv.state == 'draft' and \
                    self.doctype_id.id == inv.journal_document_type_id.id and self.journal_id.id == inv.journal_id.id:

                date = inv.date_invoice
                if date.replace("-", "") == ws['FechaCbte'] and \
                        int(float(ws['ImpTotal']) * 100) == int(float(inv.amount_total) * 100) and \
                        int(ws['PuntoVenta']) == int(inv.journal_id.point_of_sale_number) and \
                        int(ws['factura']['tipo_cbte']) == int(inv.journal_document_type_id.document_type_id.code) and \
                        ws['factura']['moneda_id'] == inv.currency_id.afip_code:

                    date2 = datetime.strptime(ws['factura']['fch_venc_cae'], '%Y%m%d').date()
                    afip_auth_code = ws['factura']['cae']
                    afip_result = ws['factura']['resultado']
                    afip_xml_request = ws['XmlRequest']
                    afip_xml_response = ws['XmlResponse']

                    inv.write({'afip_auth_code': afip_auth_code,
                               'afip_auth_code_due': date2,
                               'afip_result': afip_result,
                               'afip_xml_request': afip_xml_request,
                               'afip_xml_response': afip_xml_response})
                    inv.action_invoice_open()
                    foundf = True
                    break

        if not foundf:
            raise UserError(_('Los datos no corresponden con ninguna dentro del sistema'))



