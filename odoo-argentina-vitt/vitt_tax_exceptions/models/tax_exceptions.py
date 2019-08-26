# -*- coding: utf-8 -*-
from odoo import models, api, fields, _
from odoo.exceptions import ValidationError
import math


class TaxExceptions(models.Model):
    _name = 'account.tax.exceptions'

    sequence_id = fields.Char(string='Code', required=True, ondelete='cascade',translate=True)
    partner_id = fields.Many2one(
        'res.partner',
        string="Partner/Empresa",
        translate=True,
        domain="['|',('customer','=',True),('supplier','=',True)]",
        required=True)
    main_id_number = fields.Char(related='partner_id.main_id_number',readonly=True)
    per_tax_code = fields.Many2one(
        'account.tax',
        domain="[('type_tax_use','=','sale'),('active','=',True),('tax_group_id.tax','in',['gross_income','profits','vat']),('tax_group_id.type','=','perception')]",
        translate=True,
        string="Tax Code"
    )
    wh_tax_code = fields.Many2one(
        'account.tax',
        domain="[('type_tax_use','=','supplier'),('active','=',True),('withholding_type','in',['tabla_ganancias','arba_ws','based_on_rule'])]",
        string="Withholding Tax Code",
        translate=True,
    )
    income_reg_code = fields.Many2one('afip.tabla_ganancias.alicuotasymontos',string="Income Regime Code",)
    sdate = fields.Date(string="Start Date",required=True,translate=True,)
    edate = fields.Date(string="End Date",required=True,translate=True,)
    active = fields.Boolean(string="Active",default=True)
    ex_type = fields.Selection([('total','Total'),('parcial','Parcial')], string="Type", default='total', translate=True)
    ex_rate = fields.Float(digits=(4, 2),string="Tax Exception Rate")
    wh_ex_rate = fields.Float(digits=(4, 2),string="Withholding Tax Exception Rate")


    @api.onchange('wh_tax_code')
    def onchange_wh_tax_code(self):
        if self.wh_tax_code and self.wh_tax_code.withholding_type=='tabla_ganancias':
            self.income_reg_code = self.wh_tax_code.reg_gan_id.id

    @api.model
    def default_get(self, fields_list):
        res = dict()
        res['sequence_id'] = self.env['ir.sequence'].next_by_code('seq.tax.exceptions')
        return res

    @api.onchange('ex_rate')
    def _onchange_digit_prec1(self):
        frac, whole = math.modf(self.ex_rate)
        self.ex_rate = math.floor(self.ex_rate % 100) + frac

    @api.onchange('wh_ex_rate')
    def _onchange_digit_prec1(self):
        frac, whole = math.modf(self.wh_ex_rate)
        self.wh_ex_rate = math.floor(self.wh_ex_rate % 100) + frac

    @api.multi
    def name_get(self):
        return [(record.id, record.sequence_id) for record in self]

