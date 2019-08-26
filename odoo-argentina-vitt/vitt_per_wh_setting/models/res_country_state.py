# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import math

class ResCompany(models.Model):
    _inherit = "res.country.state"

    whtax_id = fields.Many2one('account.tax',
                               string="Withholding Tax",
                               domain="[('type_tax_use', '=', 'supplier')]",
                               translate=True,
                               track_visibility='always',)
    percep_id = fields.Many2one('account.tax',
                                string="Perception Tax",
                                domain="[('type_tax_use', '=', 'sale'),('tax_group_id.type','=','perception')]",
                                translate=True,
                                track_visibility='always')
    jurisd_id = fields.Many2one('jurisdiction.codes',string="Jurisdiction Code",translate=True)
    wh_tax_base = fields.Float(digits=(6, 4),string="Withholding Tax Base Rate",translate=True)
    perc_tax_base = fields.Float(digits=(6, 4),string="Perception Tax Base Rate",translate=True)
    type_mandatory = fields.Selection([
        ('mandatory', 'Mandatory with State Tax List'),
        ('not_mandatory', 'NOT Mandatory with State Tax List')
    ],translate=True)

    @api.onchange('wh_tax_base')
    def _onchange_digit_prec1(self):
        frac, whole = math.modf(self.wh_tax_base)
        self.wh_tax_base = math.floor(self.wh_tax_base % 100) + frac

    @api.onchange('perc_tax_base')
    def _onchange_digit_prec2(self):
        frac, whole = math.modf(self.perc_tax_base)
        self.perc_tax_base = math.floor(self.perc_tax_base % 100) + frac

