# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api, _
from openerp.exceptions import UserError
import datetime

class AfipWsConsultWizard(models.TransientModel):
    _name = 'afip.ws.consult.wizard'
    _description = 'AFIP WS Consult Wizard'

    number = fields.Integer(
        'Number',
        required=True,
    )

    @api.multi
    def confirm(self):
        self.ensure_one()
        id = self._context.get('active_id', False)
        inv = self.env['account.invoice'].search([('id','=',id)])

        if inv.afip_auth_code:
            raise UserError(_('solo sin CAE'))

        journal_document_type_id = inv.journal_document_type_id.id
        if not journal_document_type_id:
            raise UserError(_(
                'No Journal Document Class as active_id on context'))
        journal_document_type = self.env[
            'account.journal.document.type'].browse(
            journal_document_type_id)

        #return journal_document_type.get_pyafipws_consult_invoice(self.number)
        ws = journal_document_type.get_pyafipws_consult_invoice2(self.number)


        if 'factura' not in ws.keys():
            raise UserError(_('No existen datos de esa factura en la Afip'))

        if not ws['factura']['cae'] or not ws['factura']['fch_venc_cae']:
            raise UserError(_('No se pudo retraer CAE'))

        inv2 = self.env['account.invoice'].search([('afip_auth_code', '=', ws['factura']['cae'])])
        if inv2:
            raise UserError(_('you have an invoice with this CAE: %s') % (inv2.display_name2))


        date = inv.date_invoice
        if date.replace("-", "")==ws['FechaCbte'] and \
            int(float(ws['ImpTotal']) * 100) == int(float(inv.amount_total) * 100) and \
            int(ws['PuntoVenta'])==int(inv.journal_id.point_of_sale_number) and \
            int(ws['factura']['tipo_cbte'])==int(inv.journal_document_type_id.document_type_id.code) and \
            ws['factura']['moneda_id']==inv.currency_id.afip_code:

            date2 = datetime.datetime.strptime(ws['factura']['fch_venc_cae'],'%Y%m%d').date()
            afip_auth_code = ws['factura']['cae']
            afip_result = ws['factura']['resultado']
            afip_xml_request = ws['XmlRequest']
            afip_xml_response = ws['XmlResponse']

            inv.write({'afip_auth_code':afip_auth_code,
                    'afip_auth_code_due':date2,
                    'afip_result':afip_result,
                    'afip_xml_request':afip_xml_request,
                    'afip_xml_response':afip_xml_response})
            inv.action_invoice_open()
        else:
            raise UserError(_('la factura no corresponde con los datos obtenidos'))


