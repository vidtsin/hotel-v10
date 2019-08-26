# -*- coding: utf-8 -*-
from odoo import models, fields


class ResPartnerTest(models.Model):
    _inherit = 'res.partner'

    email_collections = fields.Text(string='Email collections')
