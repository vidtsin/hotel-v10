# -*- coding: utf-8 -*-
# 2018 Moogah

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class ResPartner(models.Model):
    _inherit = "res.partner"

    first_name = fields.Char(string="First Name",translate=True)
    last_name = fields.Char(string="Last Name",translate=True)
    street_number = fields.Char(string="Street Number", translate=True)
    street3 = fields.Char(string="Aditional Info", translate=True)
    neighborhood = fields.Char(string="Neighborhood", translate=True)
    floor = fields.Char(string="Floor", translate=True)
    apartment = fields.Char(string="Apartment", translate=True)
