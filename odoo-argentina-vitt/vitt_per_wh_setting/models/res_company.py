# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class ResCompany(models.Model):
    _inherit = "res.company"

    jurisdiction_comp_ids = fields.Many2many('res.country.state',string="Jurisdictions",domain="[('country_id','=', country_id)]")
