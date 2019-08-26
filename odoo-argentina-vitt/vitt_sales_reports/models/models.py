# -*- coding: utf-8 -*-
from odoo import http, models, fields, api, _
from odoo.exceptions import ValidationError

class AccountFiscalPosition(models.Model):
    _inherit = "account.fiscal.position"

    afip_code_purch = fields.Char('AFIP Code Purchase',help='For eg. This code will be used on Purcahse citi reports')

class jurisdiction_codes(models.Model):
    _name = 'jurisdiction.codes'

    name = fields.Char('codigo jurisdiccion', size=3)
    desc = fields.Char('descripcion', size=30)
    region = fields.Many2one('res.country.state',string="Provincia")


class sicore_codes(models.Model):
    _name = 'sicore.codes'

    name = fields.Char('Codigo SIFERE', size=3)
    comment = fields.Char('texto', size=60)


class sicore_codes(models.Model):
    _name = 'sicore.norm.codes'

    name = fields.Char('Arciba Norm Code', size=2, translate=True)
    comment = fields.Char('Description', size=300)
    tax_scope = fields.Selection(
        [('sale', 'Sales'),('purchase', 'Purchases'),('none', 'None'),('customer', 'Customer Payment'),('supplier', 'Supplier Payment'),],
        string='Tax Scope',
        required=True,
        default="sale",
        translate=True,)
    operation_type = fields.Selection([('withholding','Withholding'),('perception','Perception')])

    @api.multi
    def name_get(self):
        return [(code.id, "%s / %s " % (code.id, code.comment)) for code in self]


class account_tax_sicore(models.Model):
    _inherit = 'account.tax'

    sicore_tax_code = fields.Many2one('sicore.codes', string='Codigo afip')
    regcode = fields.Char('Codigo de regimen', size=3)
    jurisdiction_code = fields.Many2one('jurisdiction.codes',string='codigo jurisdiccion')
    type = fields.Selection([('factura', 'Retencion por Factura Proveedor'), ('acumulada', 'Retencion Acumulada')], string='Type', default='acumulada')
    sicore_norm = fields.Many2one('sicore.norm.codes',string="Arciba Norm Code")

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    sicore_tax_code = fields.Char('Codigo SICORE', size=3, related='tax_withholding_id.sicore_tax_code.name')
    regcode = fields.Char('Codigo de regimen', size =3, related='tax_withholding_id.regcode', readonly=False)

    @api.depends('tax_withholding_id')
    @api.onchange('tax_withholding_id')
    def _onchange_tax_withholding_id(self):
        for pay in self:
            if pay.tax_withholding_id:
                pay.regcode = pay.tax_withholding_id.regcode
            else:
                pay.regcode = ''

    @api.depends('vendorbill')
    @api.onchange('vendorbill')
    def _onchange_vendorbill(self):
        for pay in self:
            if pay.vendorbill:
                base = pay.vendorbill.amount_untaxed / pay.vendorbill.amount_total
                pay.withholdable_base_amount = pay.vendorbill.residual * base
                if pay.vendorbill.partner_id != pay.payment_group_id.partner_id:
                    raise ValidationError(_('Factura no es del mismo proveedor: ' + pay.vendorbill.document_number))


    @api.constrains('vendorbill')
    def _check_vendorbill(self):
        if self.vendorbill:
            if self.vendorbill.partner_id != self.payment_group_id.partner_id:
                raise ValidationError(_('Factura no es del mismo proveedor: ' + self.vendorbill.document_number))
        else:
            if self.tax_withholding_id.type == 'factura' and not self.vendorbill and self.partner_type == 'supplier':
                raise ValidationError(
                    _('Retencion de tipo factura sin factura proveedor asociada: ' + self.tax_withholding_id.name))


    @api.depends('customerbill')
    @api.constrains('tax_withholding_id')
    def _check_tax_withholding_id(self):
        if self.tax_withholding_id:
            if self.tax_withholding_id.type == 'factura' and not self.vendorbill and self.partner_type == 'supplier':
                raise ValidationError(
                    _('Retencion de tipo factura sin factura proveedor asociada: ' + self.tax_withholding_id.name))

            if self.tax_withholding_id.type == 'factura' and not self.customerbill and self.partner_type == 'customer':
                raise ValidationError(
                    _('Retencion de tipo factura sin factura cliente asociada: ' + self.tax_withholding_id.name))

            if self.tax_withholding_id.type == 'acumulada' and not self.tax_withholding_id.withholding_accumulated_payments \
                and self.payment_group_id.partner_type != 'customer':

                raise ValidationError(
                    _('Retencion de tipo acumulada sin tipo mensual/anual: ' + self.tax_withholding_id.name))

    @api.depends('customerbill')
    @api.onchange('customerbill')
    def _onchange_customerbill(self):
        for pay in self:
            if pay.customerbill:
                if pay.customerbill.partner_id != pay.payment_group_id.partner_id:
                    raise ValidationError(
                        _('Factura no es del mismo proveedor: ' + pay.customerbill.document_number))

    @api.constrains('customerbill')
    def _check_customerbill(self):
        if self.customerbill:
            if self.customerbill.partner_id != self.payment_group_id.partner_id:
                raise ValidationError(
                    _('Factura no es del mismo proveedor: ' + self.customerbill.document_number))

            mvl_ids = self.payment_group_id.debt_move_line_ids.mapped('invoice_id.id')
            if self.customerbill.id not in mvl_ids:
                raise ValidationError(
                    _('Factura no esta en el recibo: ' + self.customerbill.document_number))

        else:
            if self.tax_withholding_id.type == 'factura' and not self.customerbill and self.partner_type == 'customer':
                raise ValidationError(
                    _('Retencion de tipo factura sin factura cliente asociada: ' + self.tax_withholding_id.name))

                    #@api.model
    #def create(self, vals):
    #    paym = super(AccountPayment, self).create(vals)
    #    paym.payment_group_id = self.env.ref('account.payment.group').id
    #    print paym.payment_group_id
    #    return paym


    #@api.multi
    #def write(self, vals):
    #    print vals
    #    print 'aca'
    #    if self.tax_withholding_id.type == 'factura':
    #        print 'aca2'
    #        if self.vendorbill:
    #            print "3"
    #            invoice = self.env['account.invoice'].search([self.vendorbill]).id
    #            if invoice.state != 'open':
    #                raise UserError(_('Solo es posible con una factura en estado abierto'))
    #        else:
    #            print "4"
    #            raise UserError(_('Ingrese un Nro de factura'))
    #    result = super(AccountPayment, self).write(vals)
    #    return result


class ResCompany(models.Model):
    _inherit = "res.company"

    sl_arciba_taxes = fields.Many2many('account.tax',string="Impuestos ARCIBA Ventas")


class NLSettingBlock(models.TransientModel):
    _inherit = 'nl.setting.block'

    citi_pl_box = fields.Boolean(string="PL CITI mandatory fields",translate=True)
    citi_sl_box = fields.Boolean(string="SL CITI mandatory fields",translate=True)
    no_nc_partial = fields.Boolean(string="No Calcular Percepciones en NC Parciales y en Meses distintos")
    sl_arciba_tax_ids = fields.Many2many(related='company_id.sl_arciba_taxes')
    nc_paym = fields.Boolean(
        string="No Permitir validacion de Notas de Credito si ya existen Pagos asociados",
        help="Esta opcion aplica un control que no permite validar las Notas de Credito generadas desde Facturas de "
             "Proveedor si la factura de origen ya tiene un pago asociado"
    )
    nc_acc_control = fields.Boolean(
        string="Control en Notas de Credito para valores de Cuentas Contables",
        help="Esta opcion aplica un control que verifica que los valores de las Cuentas Contables en Notas de " 
             "Credito vinculadas a Facturas de Proveedor no sean superiores a las registradas en estas facturas"
    )

    @api.model
    def get_default_nc_acc_control(self, fields):
        conf = self.env['ir.config_parameter']
        if conf.get_param('check.nc_acc_control') == 'True':
            return {'nc_acc_control': True}
        else:
            return {'nc_acc_control': False}

    @api.one
    def set_nc_acc_control(self):
        conf = self.env['ir.config_parameter']
        conf.set_param('check.nc_acc_control', str(self.nc_acc_control))

    @api.model
    def get_default_nc_paym(self, fields):
        conf = self.env['ir.config_parameter']
        if conf.get_param('check.nc_paym') == 'True':
            return {'nc_paym': True}
        else:
            return {'nc_paym': False}

    @api.one
    def set_nc_paym(self):
        conf = self.env['ir.config_parameter']
        conf.set_param('check.nc_paym', str(self.nc_paym))

    @api.model
    def get_default_citi_pl_box(self, fields):
        conf = self.env['ir.config_parameter']
        if conf.get_param('check.citi_pl_box') == 'True':
            return {'citi_pl_box': True}
        else:
            return {'citi_pl_box': False}

    @api.one
    def set_citi_pl_box(self):
        conf = self.env['ir.config_parameter']
        conf.set_param('check.citi_pl_box', str(self.citi_pl_box))


    @api.model
    def get_default_citi_sl_box(self, fields):
        conf = self.env['ir.config_parameter']
        if conf.get_param('check.citi_sl_box') == 'True':
            return {'citi_sl_box': True}
        else:
            return {'citi_sl_box': False}

    @api.one
    def set_citi_sl_box(self):
        conf = self.env['ir.config_parameter']
        conf.set_param('check.citi_sl_box', str(self.citi_sl_box))

    @api.one
    def set_no_nc_partial(self):
        conf = self.env['ir.config_parameter']
        conf.set_param('check.no_nc_partial', str(self.no_nc_partial))

    @api.model
    def get_default_no_nc_partial(self, fields):
        conf = self.env['ir.config_parameter']
        if conf.get_param('check.no_nc_partial') == 'True':
            return {'no_nc_partial': True}
        else:
            return {'no_nc_partial': False}


    @api.multi
    def set_default_sl_arciba_tax_ids(self):
        for wizard in self:
            ir_values = self.env['ir.values']
            ir_values.set_default('res.company', 'sl_arciba_taxes', self.sl_arciba_tax_ids._ids, company_id=self.env.user.company_id.id)

    @api.model
    def get_default_sl_arciba_tax_ids(self, fields):
        taxes = False
        if 'sl_arciba_tax_ids' in fields:
            taxes = self.env['ir.values'].get_default('res.company', 'sl_arciba_taxes', company_id=self.env.user.company_id.id)
        return {
            'sl_arciba_tax_ids': taxes
        }
