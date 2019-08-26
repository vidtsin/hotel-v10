# -*- coding: utf-8 -*-

from odoo import fields, models


class Freight(models.Model):
    _name = 'freight.freight'
    _rec_name = 'name'

    name = fields.Char(string='Name', size=255, required=True)
    partner_id = fields.Many2one('res.partner', 'Supplier',
                                 domain="[('supplier','=',True)]")
    vehicle = fields.Char(string='Vehicle', size=255)
    volume_max = fields.Float(string='Max Volume', digits=(16, 4))
    weight_max = fields.Float(string='Max Weight', digits=(16, 4))
    active = fields.Boolean('Active', default=True)
