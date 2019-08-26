# -*- coding: utf-8 -*-
from odoo import api, fields, models

class StockPicking(models.Model):
    _inherit = "stock.picking"

    invoice_ids = fields.Many2many(
        'account.invoice',
        copy=False,
        string='Invoices',
        readonly=True)
