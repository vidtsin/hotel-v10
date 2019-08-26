# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError, Warning
import logging
import sys
import traceback
from datetime import datetime
_logger = logging.getLogger(__name__)

try:
    from pysimplesoap.client import SoapFault
except ImportError:
    _logger.debug('Can not `from pyafipws.soap import SoapFault`.')

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    mercosur_code = fields.Char(string="Codigo Mercosur",size=64)
    secretaria_code = fields.Char(string="Codigo Secretaria",size=64)

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    def update_sql(self,id, request, response):
        self._cr.execute("""UPDATE account_invoice  
                            SET afip_xml_request=%s, afip_xml_response=%s 
                            WHERE id=%s""" % (request, response, id))

    @api.multi
    def do_pyafipws_request_cae(self):
        "Request to AFIP the invoices' Authorization Electronic Code (CAE)"
        for inv in self:
            # Ignore invoices with cae
            if inv.afip_auth_code and inv.afip_auth_code_due:
                continue

            afip_ws = inv.journal_id.afip_ws
            # Ignore invoice if not ws on point of sale
            if not afip_ws:
                continue

            # get the electronic invoice type, point of sale and afip_ws:
            commercial_partner = inv.commercial_partner_id
            country = commercial_partner.country_id
            journal = inv.journal_id
            pos_number = journal.point_of_sale_number
            doc_afip_code = inv.document_type_id.code

            # authenticate against AFIP:
            ws = inv.company_id.get_connection(afip_ws).connect()

            # get the last invoice number registered in AFIP
            if afip_ws in ["wsfe","wsmtxca"]:
                ws_invoice_number = ws.CompUltimoAutorizado(
                    doc_afip_code, pos_number)
            elif afip_ws in ['wsfex','wsbfe']:
                ws_invoice_number = ws.GetLastCMP(
                    doc_afip_code, pos_number)
                if not country:
                    raise UserError(_(
                        'For WS "%s" country is required on partner' % (
                            afip_ws)))
                elif not country.code:
                    raise UserError(_(
                        'For WS "%s" country code is mandatory'
                        'Country: %s' % (
                            afip_ws, country.name)))
                elif not country.afip_code:
                    raise UserError(_(
                        'For WS "%s" country afip code is mandatory'
                        'Country: %s' % (
                            afip_ws, country.name)))

            ws_next_invoice_number = int(ws_invoice_number) + 1
            # verify that the invoice is the next one to be registered in AFIP
            if inv.invoice_number != ws_next_invoice_number:
                raise UserError(_(
                    'Error!'
                    'Invoice id: %i'
                    'Next invoice number should be %i and not %i' % (
                        inv.id,
                        ws_next_invoice_number,
                        inv.invoice_number)))

            partner_id_code = commercial_partner.main_id_category_id.afip_code
            tipo_doc = partner_id_code or '99'
            nro_doc = partner_id_code and int(
                commercial_partner.main_id_number) or "0"
            cbt_desde = cbt_hasta = cbte_nro = inv.invoice_number
            concepto = tipo_expo = int(inv.afip_concept)

            fecha_cbte = inv.date_invoice
            if afip_ws != 'wsmtxca':
                fecha_cbte = fecha_cbte.replace("-", "")

            # due and billing dates only for concept "services"
            if int(concepto) != 1:
                fecha_venc_pago = inv.date_due
                fecha_serv_desde = inv.afip_service_start
                fecha_serv_hasta = inv.afip_service_end
                if afip_ws != 'wsmtxca':
                    fecha_venc_pago = fecha_venc_pago.replace("-", "")
                    fecha_serv_desde = fecha_serv_desde.replace("-", "")
                    fecha_serv_hasta = fecha_serv_hasta.replace("-", "")
            else:
                fecha_venc_pago = fecha_serv_desde = fecha_serv_hasta = None

            if inv.mipymesf and doc_afip_code in ('201','206','211'):
                fecha_venc_pago = inv.date_due.replace('-','')

            # # invoice amount totals:
            imp_total = str("%.2f" % abs(inv.amount_total))
            # ImpTotConc es el iva no gravado
            imp_tot_conc = str("%.2f" % abs(inv.vat_untaxed_base_amount))
            imp_neto = str("%.2f" % abs(inv.vat_taxable_amount))
            imp_iva = str("%.2f" % abs(inv.vat_amount))
            imp_subtotal = str("%.2f" % abs(inv.amount_untaxed))
            imp_trib = str("%.2f" % abs(inv.other_taxes_amount))
            if doc_afip_code in ['11','12','13']: #inovice C type
                imp_tot_conc = 0
                imp_neto = str("%.2f" % (abs(inv.amount_total) - abs(inv.other_taxes_amount)))
            imp_op_ex = str("%.2f" % abs(inv.vat_exempt_base_amount))
            moneda_id = inv.currency_id.afip_code
            moneda_ctz = inv.currency_rate

            # # foreign trade data: export permit, country code, etc.:
            if inv.afip_incoterm_id:
                incoterms = inv.afip_incoterm_id.afip_code
                incoterms_ds = inv.afip_incoterm_id.name
            else:
                incoterms = incoterms_ds = None
            if int(doc_afip_code) in [19] and tipo_expo == 1:
                permiso_existente = "N" or "S"     # not used now
            else:
                permiso_existente = ""
            obs_generales = inv.comment
            if inv.payment_term_id:
                forma_pago = inv.payment_term_id.name
                obs_comerciales = inv.payment_term_id.name
            else:
                forma_pago = obs_comerciales = None
            idioma_cbte = 1     # invoice language: spanish / español

            # customer data (foreign trade):
            nombre_cliente = commercial_partner.name
            # If argentinian and cuit, then use cuit
            if country.code == 'AR' and tipo_doc == 80 and nro_doc:
                id_impositivo = nro_doc
                cuit_pais_cliente = None
            # If not argentinian and vat, use vat
            elif country.code != 'AR' and nro_doc:
                id_impositivo = nro_doc
                cuit_pais_cliente = None
            # else use cuit pais cliente
            else:
                id_impositivo = None
                if commercial_partner.is_company:
                    cuit_pais_cliente = country.cuit_juridica
                else:
                    cuit_pais_cliente = country.cuit_fisica
                if not cuit_pais_cliente:
                    raise UserError(_(
                        'No vat defined for the partner and also no CUIT set '
                        'on country'))

            domicilio_cliente = " - ".join([
                commercial_partner.name or '',
                commercial_partner.street or '',
                commercial_partner.street2 or '',
                commercial_partner.zip or '',
                commercial_partner.city or '',
            ])
            pais_dst_cmp = commercial_partner.country_id.afip_code

            # create the invoice internally in the helper
            if afip_ws == 'wsfe':
                ws.CrearFactura(
                    concepto, tipo_doc, nro_doc, doc_afip_code, pos_number,
                    cbt_desde, cbt_hasta, imp_total, imp_tot_conc, imp_neto,
                    imp_iva,
                    imp_trib, imp_op_ex, fecha_cbte, fecha_venc_pago,
                    fecha_serv_desde, fecha_serv_hasta,
                    moneda_id, moneda_ctz
                )
            elif afip_ws == 'wsmtxca':
                ws.CrearFactura(
                    concepto, tipo_doc, nro_doc, doc_afip_code, pos_number,
                    cbt_desde, cbt_hasta, imp_total, imp_tot_conc, imp_neto,
                    imp_subtotal,   # difference with wsfe
                    imp_trib, imp_op_ex, fecha_cbte, fecha_venc_pago,
                    fecha_serv_desde, fecha_serv_hasta,
                    moneda_id, moneda_ctz,
                    obs_generales   # difference with wsfe
                )
            elif afip_ws == 'wsfex':
                ws.CrearFactura(
                    doc_afip_code, pos_number, cbte_nro, fecha_cbte,
                    imp_total, tipo_expo, permiso_existente, pais_dst_cmp,
                    nombre_cliente, cuit_pais_cliente, domicilio_cliente,
                    id_impositivo, moneda_id, moneda_ctz, obs_comerciales,
                    obs_generales, forma_pago, incoterms,
                    idioma_cbte, incoterms_ds
                )
            elif afip_ws == 'wsbfe':
                ws.CrearFactura(
                    tipo_doc, nro_doc, 0, doc_afip_code, pos_number,
                    cbte_nro, fecha_cbte, imp_total, imp_neto,
                    imp_iva, imp_tot_conc, 0.0, imp_op_ex,
                    0.0, 0.0, 0.0, 0.0,
                    moneda_id, moneda_ctz
                )

            # TODO ver si en realidad tenemos que usar un vat pero no lo
            # subimos
            if afip_ws != 'wsfex' and afip_ws != 'wsbfe':
                for vat in inv.vat_taxable_ids:
                    _logger.info(
                        'Adding VAT %s' % vat.tax_id.tax_group_id.name)
                    ws.AgregarIva(
                        vat.tax_id.tax_group_id.afip_code,
                        "%.2f" % abs(vat.base),
                        # "%.2f" % abs(vat.base_amount),
                        "%.2f" % abs(vat.amount),
                    )

                for tax in inv.not_vat_tax_ids:
                    _logger.info(
                        'Adding TAX %s' % tax.tax_id.tax_group_id.name)
                    ws.AgregarTributo(
                        tax.tax_id.tax_group_id.afip_code,
                        tax.tax_id.tax_group_id.name,
                        "%.2f" % abs(tax.base),
                        # "%.2f" % abs(tax.base_amount),
                        # TODO pasar la alicuota
                        # como no tenemos la alicuota pasamos cero, en v9
                        # podremos pasar la alicuota
                        0,
                        "%.2f" % abs(tax.amount),
                    )
                if afip_ws == 'wsfe' and inv.mipymesf:
                    if doc_afip_code in ('201', '206', '211'):
                        if inv.cbu:
                            ws.AgregarOpcional(2101, inv.cbu)
                        if inv.cbu_alias:
                            ws.AgregarOpcional(2102, inv.cbu_alias)
                    if doc_afip_code in ('202', '203', '207','208','212','213'):
                        ws.AgregarOpcional(22, inv.revocation_code)


            CbteAsoc = inv.get_related_invoices_data()
            if CbteAsoc:
                ws.AgregarCmpAsoc(
                    CbteAsoc.document_type_id.code,
                    CbteAsoc.journal_id.point_of_sale_number,
                    CbteAsoc.invoice_number,
                )

            # analize line items - invoice detail
            # wsfe do not require detail
            if afip_ws != 'wsfe':
                for line in inv.invoice_line_ids:
                    codigo = line.product_id.code
                    # unidad de referencia del producto si se comercializa
                    # en una unidad distinta a la de consumo
                    if not line.uom_id.afip_code:
                        raise UserError(_(
                            'Not afip code con producto UOM %s' % (
                                line.uom_id.name)))
                    cod_mtx = line.uom_id.afip_code
                    ds = line.name
                    qty = line.quantity
                    umed = line.uom_id.afip_code
                    precio = line.price_unit
                    importe = line.price_subtotal
                    bonif = line.discount or None
                    if not line.product_id.mercosur_code.isdigit():
                        raise Warning(_('just numbers in Mercosur Code %s' % (line.product_id.mercosur_code)))
                    pro_codigo_ncm = line.product_id.mercosur_code
                    if line.product_id.secretaria_code:
                        pro_codigo_sec = line.product_id.secretaria_code
                    else:
                        pro_codigo_sec = ''
                    if afip_ws == 'wsmtxca':
                        if not line.product_id.uom_id.afip_code:
                            raise Warning(_(
                                'Not afip code con producto UOM %s' % (
                                    line.product_id.uom_id.name)))
                        u_mtx = (
                            line.product_id.uom_id.afip_code or
                            line.uom_id.afip_code)
                        # dummy true to avoid pylint error
                        if True:
                            raise Warning(
                                _('WS wsmtxca Not implemented yet'))
                        # TODO en las lineas no tenemos vat_tax_ids todavia
                        if self.invoice_id.type in ('out_invoice', 'in_invoice'):
                            iva_id = line.vat_tax_ids.tax_code_id.afip_code
                        else:
                            iva_id = line.vat_tax_ids.ref_tax_code_id.afip_code
                        vat_taxes_amounts = line.vat_tax_ids.compute_all(
                            line.price_unit, line.quantity,
                            product=line.product_id,
                            partner=inv.partner_id)
                        imp_iva = vat_taxes_amounts[
                            'total_included'] - vat_taxes_amounts['total']
                        ws.AgregarItem(
                            u_mtx, cod_mtx, codigo, ds, qty, umed,
                            precio, bonif, iva_id, imp_iva, importe + imp_iva)
                    elif afip_ws == 'wsfex':
                        ws.AgregarItem(
                            codigo, ds, qty, umed, precio, importe,
                            bonif)
                    elif afip_ws == 'wsbfe':
                        for tribute in line.product_id.taxes_id:
                            if tribute.tax_group_id.tax == 'vat':
                                iva_id = tribute.tax_group_id.afip_code
                                break
                        ws.AgregarItem(
                            pro_codigo_ncm, pro_codigo_sec, str(ds), qty, umed, precio, bonif,
                            iva_id, importe)

            # Request the authorization! (call the AFIP webservice method)
            vto = None
            msg = False
            try:
                if afip_ws == 'wsfe':
                    ws.CAESolicitar()
                    vto = ws.Vencimiento
                elif afip_ws == 'wsmtxca':
                    ws.AutorizarComprobante()
                    vto = ws.Vencimiento
                elif afip_ws == 'wsfex':
                    ws.Authorize(inv.id)
                    vto = ws.FchVencCAE
                elif afip_ws == 'wsbfe':
                    ws.Authorize(inv.id)
                    vto = ws.FchVencCAE
            except SoapFault as fault:
                self.update_sql(self.id,ws.XmlRequest,ws.XmlResponse)
                msg = 'Falla SOAP %s: %s' % (
                    fault.faultcode, fault.faultstring)
            except Exception, e:
                self.update_sql(self.id,ws.XmlRequest,ws.XmlResponse)
                msg = e
            except Exception:
                self.update_sql(self.id,ws.XmlRequest,ws.XmlResponse)
                if ws.Excepcion:
                    # get the exception already parsed by the helper
                    msg = ws.Excepcion
                else:
                    # avoid encoding problem when raising error
                    msg = traceback.format_exception_only(
                        sys.exc_type,
                        sys.exc_value)[0]

            inv.write({
                'afip_auth_verify_result': ws.Resultado,
                'afip_auth_verify_observation': '%s%s' % (ws.Obs, ws.ErrMsg)
            })
            print "--------------------"
            print ws.XmlRequest
            print "--------------------"
            if msg:
                raise UserError(_('AFIP Validation Error. %s' % msg))

            msg = u"\n".join([ws.Obs or "", ws.ErrMsg or ""])
            if not ws.CAE or ws.Resultado != 'A':
                raise UserError(_('AFIP Validation Error. %s' % msg))
            # TODO ver que algunso campos no tienen sentido porque solo se
            # escribe aca si no hay errores
            _logger.info('CAE solicitado con exito. CAE: %s. Resultado %s' % (
                ws.CAE, ws.Resultado))
            inv.write({
                'afip_auth_mode': 'CAE',
                'afip_auth_code': ws.CAE,
                'afip_auth_code_due': vto,
                'afip_result': ws.Resultado,
                'afip_message': msg,
                'afip_xml_request': ws.XmlRequest,
                'afip_xml_response': ws.XmlResponse,
                'state': 'open',
            })

    @api.multi
    def write(self, vals):
        res = super(AccountInvoice, self).write(vals)
        for inv in self:
            if inv.date_invoice:
                orig_month = datetime.strptime(inv.date_invoice, "%Y-%m-%d").strftime('%m')
                today_month = datetime.today().strftime('%m')
                if orig_month != today_month:
                    raise UserError(_('You can send invoices in the same current month only'))
            if inv.mipymesf:
                if not inv.date_due:
                    raise UserError(_('You can send invoices in the same current month only'))
                if inv.type == 'out_refund':
                    if not inv.cbu:
                        raise UserError(_('You should complete Issuer CBU mipymes'))
                    if not inv.bank_account_id:
                        raise UserError(_('You should complete Bank Account mipymes'))
            vals.update({'mipymesf_read_only': inv.mipymesf})
        return res

class AfipwsConnection(models.Model):
    _inherit = "afipws.connection"

    @api.model
    def _get_ws(self, afip_ws):
        """
        Method to be inherited
        """
        ws = super(AfipwsConnection, self)._get_ws(afip_ws)
        if afip_ws == 'wsfe':
            from pyafipws.wsfev1 import WSFEv1
            ws = WSFEv1()
            if hasattr(ws, 'HOMO'):
                if self.type == 'production':
                    ws.HOMO = False
                else:
                    ws.HOMO = True
        elif afip_ws == "wsfex":
            from pyafipws.wsfexv1 import WSFEXv1
            ws = WSFEXv1()
            if hasattr(ws, 'HOMO'):
                if self.type == 'production':
                    ws.HOMO = False
                else:
                    ws.HOMO = True
        elif afip_ws == "wsmtxca":
            from pyafipws.wsmtx import WSMTXCA
            ws = WSMTXCA()
            if hasattr(ws, 'HOMO'):
                if self.type == 'production':
                    ws.HOMO = False
                else:
                    ws.HOMO = True
        elif afip_ws == "wscdc":
            from pyafipws.wscdc import WSCDC
            ws = WSCDC()
            if hasattr(ws, 'HOMO'):
                if self.type == 'production':
                    ws.HOMO = False
                else:
                    ws.HOMO = True
        elif afip_ws == "ws_sr_padron_a4":
            from pyafipws.ws_sr_padron import WSSrPadronA4
            ws = WSSrPadronA4()
            if self.type == 'production':
                ws.HOMO = False
                ws.WSDL = "https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA4?wsdl"
            else:
                ws.HOMO = True
        elif afip_ws == "ws_sr_constancia_inscripcion":
            from pyafipws.ws_sr_padron import WSSrPadronA5
            ws = WSSrPadronA5()
            if self.type == 'production':
                ws.HOMO = False
                ws.WSDL = "https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA5?wsdl"
            else:
                ws.HOMO = True
        elif afip_ws == "wsbfe":
            from pyafipws.wsbfev1 import WSBFEv1
            ws = WSBFEv1()
            if self.type == 'production':
                ws.HOMO = False
                ws.WSDL = "https://servicios1.afip.gov.ar/wsbfev1/service.asmx?WSDL"
            else:
                ws.HOMO = True
                ws.WSDL = "https://wswhomo.afip.gov.ar/wsbfev1/service.asmx?WSDL"
        return ws

    @api.model
    def get_afip_ws_url(self, afip_ws, environment_type):
        if afip_ws == 'wsfe':
            if environment_type == 'production':
                afip_ws_url = (
                    'https://servicios1.afip.gov.ar/wsfev1/service.asmx')
            else:
                afip_ws_url = (
                    'https://wswhomo.afip.gov.ar/wsfev1/service.asmx')
        elif afip_ws == 'wsfex':
            if environment_type == 'production':
                afip_ws_url = (
                    'https://servicios1.afip.gov.ar/wsfexv1/service.asmx')
            else:
                afip_ws_url = (
                    'https://wswhomo.afip.gov.ar/wsfexv1/service.asmx')
        elif afip_ws == 'wsbfe':
            #raise UserError('AFIP WS %s Not implemented yet' % afip_ws)
            if environment_type == 'production':
                afip_ws_url = (
                    'https://servicios1.afip.gov.ar/wsbfev1/service.asmx')
            else:
                afip_ws_url = (
                    'https://wswhomo.afip.gov.ar/wsbfev1/service.asmx')
        elif afip_ws == 'wsmtxca':
            raise UserError('AFIP WS %s Not implemented yet' % afip_ws)
            # if environment_type == 'production':
            #     afip_ws_url = (
            #         'https://serviciosjava.afip.gob.ar/wsmtxca/services/'
            #         'MTXCAService')
            # else:
            #     afip_ws_url = (
            #         'https://fwshomo.afip.gov.ar/wsmtxca/services/'
            #         'MTXCAService')
        elif afip_ws == 'wscdc':
            if environment_type == 'production':
                afip_ws_url = (
                    'https://servicios1.afip.gov.ar/WSCDC/service.asmx')
            else:
                afip_ws_url = 'https://wswhomo.afip.gov.ar/WSCDC/service.asmx'
        elif afip_ws == 'ws_sr_padron_a4':
            if environment_type == 'production':
                afip_ws_url = (
                    'https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA4')
            else:
                afip_ws_url = (
                    'https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA4')
        elif afip_ws == 'ws_sr_constancia_inscripcion':
            if environment_type == 'production':
                afip_ws_url = (
                    'https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA5')
            else:
                afip_ws_url = (
                    'https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA5')

        if afip_ws_url:
            return afip_ws_url
        afip_ws_url = super(AfipwsConnection, self).get_afip_ws_url(
            afip_ws, environment_type)


        return afip_ws_url
