# -*- coding: utf-8 -*-

from odoo import fields, models

class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'
    
    jurisdiction_ids = fields.Many2many(related='company_id.jurisdiction_comp_ids')
    country_id = fields.Many2one(related='company_id.country_id')