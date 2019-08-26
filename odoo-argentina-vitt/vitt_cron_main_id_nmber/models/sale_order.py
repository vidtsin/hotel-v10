# -*- coding: utf-8 -*-
# 2018 Moogah

from odoo import models, api, fields, _
from odoo.exceptions import ValidationError

class SaleOrder(models.Model):
    _inherit = 'res.partner'

    def run_update_main_id_number(self):
        partners = self.env['res.partner'].search([])
        for partner in partners:
            if partner.main_id_number:
                partner._compute_main_id_number()

