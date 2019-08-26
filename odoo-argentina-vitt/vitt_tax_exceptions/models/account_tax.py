# -*- coding: utf-8 -*-
from odoo import models, api, fields, _
from dateutil.relativedelta import relativedelta
from datetime import datetime
import xmlrpclib
from odoo.exceptions import ValidationError, Warning, UserError

import logging
_logger = logging.getLogger(__name__)

class ResCompany(models.Model):
    _inherit = 'res.company'

    def get_agip_data(self,partner,sdate,edate,apg=False):
        if not self.agip_user or not self.agip_password:
            raise Warning(_('Complete user y password del servdor AGIP en seteo compania'))

        #SERVER REAL
        server = "http://padrones.moogah.com:80"
        database = "padrones"

        #SERVER TEST
        #server = "http://127.0.0.1:8069"
        #database = "wh"
        user = self.agip_user
        pwd = self.agip_password
        padron = list()
        data = dict()

        try:
            common = xmlrpclib.ServerProxy('%s/xmlrpc/2/common' % server)
        except Exception as e:
            raise Warning(_('Error conectandose con el servicio de AGIP, comuniquese con el soporte de Moogah'))
        try:
                uid = common.authenticate(database, user, pwd, {})
        except Exception as e:
            raise Warning(_('Error user/pass erroneo para servidor AGIP, comuniquese con el soporte de Moogah'))

        try:
            OdooApi = xmlrpclib.ServerProxy('%s/xmlrpc/2/object' % server)
            filters = [[['main_id_number', '=', partner.main_id_number],['sdate','<=',str(sdate)],['edate','>=',str(edate)]]]
            padron = OdooApi.execute_kw(database, uid, pwd, 'ret.padron', 'search_read', filters)
        except Exception as e:
            raise Warning(_('Error, usuario sin acceso a los padrones, comuniquese con el soporte de Moogah'))

        if padron:
            data = {
                'numero_comprobante': 'nuestro server',
                'codigo_hash': '',
                'alicuota_percepcion':padron[0]['percep_rate'],
                'alicuota_retencion': padron[0]['whold_rate'],
                'grupo_percepcion': padron[0]['percep_group'],
                'grupo_retencion': padron[0]['whold_group'],
                'from_date': padron[0]['sdate'],
                'to_date': padron[0]['edate'],
            }
            _logger.info('We get the following data: \n%s' % data)

        return data

class AI(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def get_taxes_values(self):
        tax_grouped = {}
        for line in self.invoice_line_ids:
            price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.invoice_line_tax_ids.with_context(date_invoice=self.date_invoice).compute_all(price_unit, self.currency_id, line.quantity, line.product_id, self.partner_id,
                                                          self.partner_shipping_id.state_id or self.partner_id.state_id)['taxes']
            for tax in taxes:
                val = self._prepare_tax_line_vals(line, tax)
                key = self.env['account.tax'].browse(tax['id']).get_grouping_key(val)

                if key not in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base'] += val['base']
        return tax_grouped

    @api.onchange('date_invoice')
    def onchange_date_invoice(self):
        self._onchange_invoice_line_ids()
        return super(AI, self).onchange_date_invoice()


class AIL(models.Model):
    _inherit = 'account.invoice.line'

    @api.one
    @api.depends('price_unit', 'discount', 'invoice_line_tax_ids', 'quantity',
        'product_id', 'invoice_id.partner_id', 'invoice_id.currency_id', 'invoice_id.company_id',
        'invoice_id.date_invoice')
    def _compute_price(self):
        currency = self.invoice_id and self.invoice_id.currency_id or None
        price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
        taxes = False
        if self.invoice_line_tax_ids:
            taxes = self.invoice_line_tax_ids.with_context(date_invoice=self.invoice_id.date_invoice).compute_all(
                price, currency, self.quantity, product=self.product_id, partner=self.invoice_id.partner_id,
                jur=self.invoice_id.partner_shipping_id.state_id or self.invoice_id.partner_id.state_id
            )

        self.price_subtotal = price_subtotal_signed = taxes['total_excluded'] if taxes else self.quantity * price
        if self.invoice_id.currency_id and self.invoice_id.company_id and self.invoice_id.currency_id != self.invoice_id.company_id.currency_id:
            price_subtotal_signed = self.invoice_id.currency_id.with_context(date=self.invoice_id.date_invoice).compute(price_subtotal_signed, self.invoice_id.company_id.currency_id)
        sign = self.invoice_id.type in ['in_refund', 'out_refund'] and -1 or 1
        self.price_subtotal_signed = price_subtotal_signed * sign


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.multi
    def get_arba_alicuota_percepcion(self,tax,jur):
        if hasattr(self, 'company_id'):
            company = self.company_id
        else:
            company = self._context.get('invoice_company')

        invoice_date = self._context.get('date_invoice')
        if not invoice_date:
            invoice_date = fields.Date.today()

        if datetime.strptime(str(invoice_date), '%Y-%m-%d').month > datetime.strptime(str(fields.Date.today()), '%Y-%m-%d').month \
            and datetime.strptime(str(invoice_date), '%Y-%m-%d').year == datetime.strptime(str(fields.Date.today()), '%Y-%m-%d').year:
            return -1

        #print invoice_date
        # if hasattr(self, 'date_invoice'):
        #     invoice_date = self._context.get('date_invoice')
        # elif hasattr(self, 'invoice_date'):
        #     invoice_date = self._context.get('invoice_date')
        # else:
        #     invoice_date = fields.Date.today()

        if invoice_date and company:
            if tax.tax_control == 'control':
                taxregion = tax.jurisdiction_code.region
                invregion = jur
                if tax.jurisdiction_code.region.type_mandatory == 'mandatory':
                    if taxregion != invregion:
                        return 0
                    else:
                        date = datetime.strptime(invoice_date, '%Y-%m-%d')
                        arba = self.get_arba_data(company, date)
                        if not arba.numero_comprobante:
                            return (invregion.perc_tax_base / 100)
                        else:
                            return arba.alicuota_percepcion / 100.0

                else:
                    raise ValidationError(_('el impuesto %s esta seteado como web service, control y no obligatorio, no es valido, comuniquese con soporte de Moogah' % tax.name))
            else:
                date = datetime.strptime(invoice_date, '%Y-%m-%d')
                arba = self.get_arba_data(company, date)
                if not arba.numero_comprobante:
                    return 0
                else:
                    _logger.info('1 - Alicuota arba Recibida para calculo percepcion: %s' % arba.alicuota_percepcion)
                    return arba.alicuota_percepcion / 100.0
        return 0

    @api.multi
    def get_agip_alicuota_percepcion(self,tax,jur):
        if hasattr(self, 'company_id'):
            company = self.company_id
        else:
            company = self._context.get('invoice_company')

        invoice_date = self._context.get('date_invoice')
        if not invoice_date:
            invoice_date = fields.Date.today()

        if datetime.strptime(str(invoice_date), '%Y-%m-%d').month > datetime.strptime(str(fields.Date.today()), '%Y-%m-%d').month \
            and datetime.strptime(str(invoice_date), '%Y-%m-%d').year == datetime.strptime(str(fields.Date.today()), '%Y-%m-%d').year:

            return -1

        # if hasattr(self, 'date_invoice'):
        #     invoice_date = self._context.get('date_invoice')
        # elif hasattr(self, 'invoice_date'):
        #     invoice_date = self._context.get('invoice_date')
        # else:
        #     invoice_date = fields.Date.today()


        if invoice_date and company and self.company_id.agip_enabler:
            if tax.tax_control == 'control':
                taxregion = tax.jurisdiction_code.region
                invregion = jur
                if tax.jurisdiction_code.region.type_mandatory == 'mandatory':
                    if taxregion != invregion:
                        return 0
                    else:
                        date = datetime.strptime(invoice_date, '%Y-%m-%d')
                        arba = self.get_agip_data(company, date)
                        if not arba.numero_comprobante:
                            return (invregion.perc_tax_base / 100)
                        else:
                            return arba.alicuota_percepcion / 100.0

                else:
                    raise ValidationError(_('el impuesto %s esta seteado como web service, control y no obligatorio, no es valido, comuniquese con soporte de Moogah' % tax.name))
            else:
                date = datetime.strptime(invoice_date, '%Y-%m-%d')
                arba = self.get_agip_data(company, date)
                if not arba.numero_comprobante:
                    return 0
                else:
                    _logger.info('2 - Alicuota arba Recibida para calculo percepcion: %s' % arba.alicuota_percepcion)
                    return arba.alicuota_percepcion / 100.0
        return 0

    @api.multi
    def get_arba_alicuota_retencion(self, company, date):
        if datetime.strptime(str(date), '%Y-%m-%d').month > datetime.strptime(str(fields.Date.today()), '%Y-%m-%d').month \
            and datetime.strptime(str(date), '%Y-%m-%d').year == datetime.strptime(str(fields.Date.today()), '%Y-%m-%d').year:

            return -1

        arba = self.get_arba_data(company, date)
        if not arba.numero_comprobante:
            return -1 #IF NOT IN PADRON RETURN THIS INSTEAD OF ZERO
        _logger.info('3 - Alicuota arba Recibida para calculo retencion: %s' % arba.alicuota_retencion)
        return arba.alicuota_retencion / 100.0


    def get_agip_alicuota_retencion(self,company,paydate,apg=False):
        if datetime.strptime(str(paydate), '%Y-%m-%d').month > datetime.strptime(str(fields.Date.today()), '%Y-%m-%d').month \
            and datetime.strptime(str(paydate), '%Y-%m-%d').year == datetime.strptime(str(fields.Date.today()), '%Y-%m-%d').year:

            return -1

        agip = self.get_agip_data(company,paydate,apg)
        if not agip.numero_comprobante:
            return -1 #IF NOT IN PADRON RETURN THIS INSTEAD OF ZERO
        _logger.info('Alicuota agip Recibida para calculo retencion: %s' % agip.alicuota_retencion)
        return agip.alicuota_retencion / 100.0

    @api.multi
    def get_agip_data(self, company, date, apg=False):
        self.ensure_one()
        from_date = (date + relativedelta(day=1)).strftime('%Y%m%d')
        to_date = (date + relativedelta(
            day=1, days=-1, months=+1)).strftime('%Y%m%d')
        commercial_partner = self.commercial_partner_id
        arba = self.arba_alicuot_ids.search([
            ('from_date', '=', from_date),
            ('to_date', '=', to_date),
            ('service', '=', 'AGIP WS'),
            ('company_id', '=', company.id),
            ('partner_id', '=', commercial_partner.id)], limit=1)
        if not arba:
            arba_data = dict()
            arba_data = company.get_agip_data(
                commercial_partner,
                from_date, to_date,
                apg,
            )
            arba_data['partner_id'] = commercial_partner.id
            arba_data['company_id'] = company.id
            arba_data['service'] = 'AGIP WS'
            arba_data['from_date'] = from_date
            arba_data['to_date'] = to_date
            arba = self.arba_alicuot_ids.sudo().create(arba_data)
        return arba

class AccountTax(models.Model):
    _inherit = "account.tax"

    amount_type = fields.Selection(selection_add=[('code2', 'Web Service')])
    service_id = fields.Selection([('arba_ws','ARBA WS'),('agip_ws','AGIP WS')],string='Services',translate=True)
    withholding_type = fields.Selection(
        selection_add=([('agip_ws', 'WS Agip')])
    )

    #overwritten
    @api.multi
    def compute_all(self, price_unit, currency=None, quantity=1.0, product=None, partner=None, jur=None):
        # NEW
        date_invoice = self._context.get('date_invoice')

        if len(self) == 0:
            company_id = self.env.user.company_id
        else:
            company_id = self[0].company_id
        if not currency:
            currency = company_id.currency_id
        taxes = []
        prec = currency.decimal_places
        round_tax = False if company_id.tax_calculation_rounding_method == 'round_globally' else True
        round_total = True
        if 'round' in self.env.context:
            round_tax = bool(self.env.context['round'])
            round_total = bool(self.env.context['round'])

        if not round_tax:
            prec += 5

        base_values = self.env.context.get('base_values')
        if not base_values:
            total_excluded = total_included = base = round(price_unit * quantity, prec)
        else:
            total_excluded, total_included, base = base_values

        for tax in self.sorted(key=lambda r: r.sequence):

            if tax.amount_type == 'group':
                children = tax.children_tax_ids.with_context(base_values=(total_excluded, total_included, base))
                ret = children.with_context(date_invoice=date_invoice).compute_all(price_unit, currency, quantity, product, partner,jur)
                total_excluded = ret['total_excluded']
                base = ret['base'] if tax.include_base_amount else base
                total_included = ret['total_included']
                tax_amount = total_included - total_excluded
                taxes += ret['taxes']
                continue

            #NEW
            tax_amount = tax.with_context(date_invoice=date_invoice)._compute_amount(base, price_unit, quantity, product, partner,jur)

            if not round_tax:
                tax_amount = round(tax_amount, prec)
            else:
                tax_amount = currency.round(tax_amount)

            if tax.price_include:
                total_excluded -= tax_amount
                base -= tax_amount
            else:
                total_included += tax_amount

            tax_base = base

            if tax.include_base_amount:
                base += tax_amount

            taxes.append({
                'id': tax.id,
                'name': tax.with_context(**{'lang': partner.lang} if partner else {}).name,
                'amount': tax_amount,
                'base': tax_base,
                'sequence': tax.sequence,
                'account_id': tax.account_id.id,
                'refund_account_id': tax.refund_account_id.id,
                'analytic': tax.analytic,
            })

        return {
            'taxes': sorted(taxes, key=lambda k: k['sequence']),
            'total_excluded': currency.round(total_excluded) if round_total else total_excluded,
            'total_included': currency.round(total_included) if round_total else total_included,
            'base': base,
        }

    def _compute_amount(self, base_amount, price_unit, quantity=1.0, product=None, partner=None, jur=None):
        self.ensure_one()
        res = super(AccountTax, self)._compute_amount(base_amount, price_unit, quantity, product, partner)

        date_invoice = self._context.get('date_invoice')
        if self.amount_type == 'code2':
            if partner.company_type != 'person':
                if self.service_id == 'arba_ws':
                    result = price_unit * quantity * partner.with_context(date_invoice=date_invoice).get_arba_alicuota_percepcion(self,jur)
                    return result
                if self.service_id == 'agip_ws':
                    result = price_unit * quantity * partner.with_context(date_invoice=date_invoice).get_agip_alicuota_percepcion(self,jur)
                    return result
                raise ValidationError(_('el impuesto %s no tiene ningun webservice seleccionado' % self.name))
            else:
                return 0.0

        if self.amount_type in ['percent','division']:
            if self.jurisdiction_code and self.tax_control == 'control':
                if self.jurisdiction_code.region.type_mandatory == 'mandatory':
                    if self._context.get('default_invoice_id'):
                        inv = self.env['account.invoice'].search([('id', '=', self._context.get('default_invoice_id'))])
                        taxregion = self.jurisdiction_code.region
                        invregion = jur
                        if taxregion != invregion:
                            return 0
                        else:
                            return (invregion.perc_tax_base / 100)

        return res

    @api.multi
    def get_withholding_vals(self, payment_group,acc_ids_list=[]):
        self.ensure_one()

        withholdable_invoiced_amount = payment_group.selected_debt_untaxed
        withholdable_advanced_amount = 0.0
        if self.withholding_advances:
            withholdable_advanced_amount = payment_group.unreconciled_amount

        to_date = fields.Date.from_string(payment_group.payment_date) or datetime.date.today()
        accumulated_amount = previous_withholding_amount = 0.0
        withholding_accumulated_payments = (self.withholding_accumulated_payments)
        if withholding_accumulated_payments:
            previos_payments_domain = [
                ('partner_id.commercial_partner_id', '=',payment_group.commercial_partner_id.id),
                ('state', '=', 'posted')
            ]
            if withholding_accumulated_payments == 'month':
                from_relative_delta = relativedelta(day=1)
            elif withholding_accumulated_payments == 'year':
                from_relative_delta = relativedelta(day=1, month=1)
            from_date = to_date + from_relative_delta
            previos_payments_domain += [('payment_date', '<=', to_date),('payment_date', '>=', from_date)]
            same_period_payments = self.env['account.payment.group'].search(previos_payments_domain + [('id', '!=', payment_group.id)])
            for same_period_payment_group in same_period_payments:
                #print '-------------------------------------- entrando acumulado'
                accumulated_amount += same_period_payment_group._compute_selected_debt_function(self) #invoiced_debt_untaxed)
                #print '-------------------------------------- saliendo acumulado'
                if self.withholding_advances:
                    accumulated_amount += (same_period_payment_group.unmatched_amount)
            previous_withholding_amount = sum(self.env['account.payment'].search(previos_payments_domain + [('tax_withholding_id', '=', self.id)]).mapped('amount'))

        valsarray = {}
        rest_paym = paymt = payp = total_amount = withholdable_invoiced_amount = 0.0
        pay_amt = payment_group.to_pay_amount
        sign = payment_group.partner_type == 'supplier' and -1.0 or 1.0
        payment_group.to_pay_move_line_ids = payment_group.to_pay_move_line_ids.sorted(key='date_maturity')

        exception = self.env['account.tax.exceptions'].search([
            ('partner_id', '=', payment_group.partner_id.id),
            ('wh_tax_code', '=', self.id),
            ('sdate', '<=', payment_group.payment_date),
            ('edate', '>=', payment_group.payment_date),
            ('active', '=', True)]
        )

        for line in payment_group.to_pay_move_line_ids:

            if exception:
                if exception.ex_type == 'total':
                    break

            if rest_paym < pay_amt:
                paym = -line.amount_residual
                paymt += paym
                if  paymt <= pay_amt:
                    rest_paym += paym
                    payp =  paym
                else:
                    payp =  pay_amt - rest_paym
                    rest_paym += pay_amt - rest_paym

                to_pay_amount = -(payp * sign)
                untax_amt = payment_group._getuntaxedvalue(line.invoice_id,to_pay_amount,acc_ids_list,self.withholding_amount_type)
                invoice_sign = line.invoice_id.type in ['in_refund'] and -1.0 or 1.0
                untax_amt = untax_amt * invoice_sign
                withholdable_invoiced_amount = untax_amt

                total_amount = (accumulated_amount + withholdable_advanced_amount + withholdable_invoiced_amount)

                withholding_non_taxable_minimum = self.withholding_non_taxable_minimum
                withholding_non_taxable_amount = self.withholding_non_taxable_amount
                withholdable_base_amount = (
                    (total_amount > withholding_non_taxable_minimum) and
                    (total_amount - withholding_non_taxable_amount) or 0.0)

                comment = False
                if self.withholding_type == 'code':
                    localdict = {
                        'withholdable_base_amount': withholdable_base_amount,
                        'payment': payment_group,
                        'partner': payment_group.commercial_partner_id,
                        'withholding_tax': self,
                    }
                    eval(self.withholding_python_compute, localdict,mode="exec", nocopy=True)
                    period_withholding_amount = localdict['result']
                else:
                    rule = self._get_rule(payment_group)
                    #print 'rule ', rule
                    percentage = 0.0
                    fix_amount = 0.0
                    if rule:
                        percentage = rule.percentage/100
                        fix_amount = rule.fix_amount
                        comment = '%s x %s + %s' % (
                            withholdable_base_amount,
                            percentage,
                            fix_amount)

                    period_withholding_amount = (
                        (total_amount > withholding_non_taxable_minimum) and (
                            withholdable_base_amount * percentage + fix_amount) or 0.0)

                    valsarray[line.invoice_id.id] = {
                        'withholdable_invoiced_amount': withholdable_invoiced_amount,
                        'withholdable_advanced_amount': withholdable_advanced_amount,
                        'accumulated_amount': accumulated_amount,
                        'total_amount': total_amount,
                        'withholding_non_taxable_minimum': withholding_non_taxable_minimum,
                        'withholding_non_taxable_amount': withholding_non_taxable_amount,
                        'withholdable_base_amount': withholdable_base_amount,
                        'period_withholding_amount': period_withholding_amount,
                        'previous_withholding_amount': previous_withholding_amount,
                        'payment_group_id': payment_group.id,
                        'tax_withholding_id': self.id,
                        'automatic': True,
                        'comment': comment,
                        'payment_date': payment_group.payment_date,
                        'wh_perc': percentage*100,
                        'regcode': self.reg_gan_id.codigo_de_regimen,
                    }
                accumulated_amount += untax_amt


        #INHERITED PART
        vals = {}
        for line in payment_group.to_pay_move_line_ids:
            if line.invoice_id.id in valsarray.keys():
                vals = valsarray[line.invoice_id.id]
                base_amount = vals['withholdable_base_amount']
                commercial_partner = payment_group.commercial_partner_id

                if self.withholding_type == 'arba_ws' or self.withholding_type == 'agip_ws':
                    if commercial_partner.gross_income_type == 'no_liquida':
                        vals['period_withholding_amount'] = 0.0
                    else:
                        payment_date = (payment_group.payment_date and
                            fields.Date.from_string(payment_group.payment_date) or datetime.date.today())

                        if self.withholding_type == 'arba_ws':
                            alicuota = commercial_partner.get_arba_alicuota_retencion(
                                payment_group.company_id,
                                payment_date,
                            )

                        if self.withholding_type == 'agip_ws':
                            if self.company_id.agip_enabler:
                                alicuota = commercial_partner.get_agip_alicuota_retencion(
                                    payment_group.company_id,
                                    payment_date,
                                    payment_group,
                                )
                            else:
                                alicuota = 0

                        _logger.info('Alicuota Recibida para calculo Final: %s' % alicuota)
                        if alicuota == -1:
                            testf = False
                            if self.tax_control == 'control':
                                if self.jurisdiction_code.region.type_mandatory == 'mandatory':
                                    testf = True
                            else:
                                testf = True
                            if testf:
                                alicuota = self.jurisdiction_code.region.wh_tax_base
                                alicuota = alicuota/100
                                if not alicuota:
                                    alicuota = 0.0

                        if exception.ex_type == 'parcial':
                            alicuota = exception.wh_ex_rate/100

                        amount = base_amount * (alicuota)
                        vals['comment'] = "%s x %s" % (base_amount, alicuota)
                        vals['period_withholding_amount'] = amount
                        vals['wh_perc'] = alicuota*100
                        vals['journal_id'] = self.journal_id.id

                elif self.withholding_type == 'tabla_ganancias':
                    amount = 0.0
                    #regimen = payment_group.regimen_ganancias_id
                    regimen = self.reg_gan_id

                    imp_ganancias_padron = commercial_partner.imp_ganancias_padron
                    if (payment_group.retencion_ganancias != 'nro_regimen' or not regimen):
                        # if amount zero then we dont create withholding
                        amount = 0.0
                    elif not imp_ganancias_padron:
                        raise UserError(
                            'El partner %s no tiene configurada inscripcion en '
                            'impuesto a las ganancias' % commercial_partner.name)
                    elif imp_ganancias_padron == 'EX':
                        # if amount zero then we dont create withholding
                        amount = 0.0
                    # TODO validar excencion actualizada
                    elif imp_ganancias_padron == 'AC':
                        # alicuota inscripto
                        non_taxable_amount = (
                            regimen.montos_no_sujetos_a_retencion)
                        vals['withholding_non_taxable_amount'] = non_taxable_amount
                        if base_amount < non_taxable_amount:
                            base_amount = 0.0
                        else:
                            base_amount -= non_taxable_amount
                        vals['withholdable_base_amount'] = base_amount
                        if regimen.porcentaje_inscripto == -1:
                            escala = self.env['afip.tabla_ganancias.escala'].search([
                                ('importe_desde', '<', base_amount),
                                ('importe_hasta', '>=', base_amount),
                            ], limit=1)
                            # if not escala:
                            #     raise UserError(
                            #         'No se encontro ninguna escala para el monto'
                            #         ' %s' % (base_amount))
                            if escala:
                                amount = escala.importe_fijo
                                amount += (escala.porcentaje / 100.0) * (base_amount - escala.importe_excedente)
                                vals['comment'] = "%s + (%s x %s)" % (
                                    escala.importe_fijo,
                                    base_amount - escala.importe_excedente,
                                    escala.porcentaje / 100.0)
                                vals['wh_perc'] = escala.porcentaje
                        else:
                            amount = base_amount * (regimen.porcentaje_inscripto / 100.0)
                            vals['comment'] = "%s x %s" % (base_amount, regimen.porcentaje_inscripto / 100.0)
                            vals['wh_perc'] = regimen.porcentaje_inscripto
                    elif imp_ganancias_padron == 'NI':
                        # alicuota no inscripto
                        amount = base_amount * (regimen.porcentaje_no_inscripto / 100.0)
                        vals['comment'] = "%s x %s" % (base_amount, regimen.porcentaje_no_inscripto / 100.0)
                        vals['wh_perc'] = regimen.porcentaje_no_inscripto
                    elif imp_ganancias_padron == 'NC':
                        # no corresponde, no impuesto
                        amount = 0.0
                    vals['description'] = regimen.codigo_de_regimen
                    vals['period_withholding_amount'] = amount
                valsarray[line.invoice_id.id] = vals

        return valsarray
