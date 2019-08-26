# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import timedelta


class ResCompany(models.Model):
    _inherit = "res.company"

    purchase_invoices = fields.Float("Purchase Invoices", digits=(16, 2))
    sales_invoices = fields.Float("Sales Invoices", digits=(16, 2))
    purchase_orders = fields.Float("Purchase Orders", digits=(16, 2))
    sales_orders = fields.Float("Sales Orders", digits=(16, 2))

    purchase_invoices_user_ids = fields.Many2many(
        'res.users',
        'company_users_purchase_invoices',
        'company_id', 'user_id',
        "Purchase Invoices"
    )
    sales_invoices_user_ids = fields.Many2many(
        'res.users',
        'res_company_users_sales_invoices',
        'company_id', 'user_id',
        "Sales Invoices"
    )
    purchase_orders_user_ids = fields.Many2many(
        'res.users',
        'res_company_users_purchase_orders',
        'company_id', 'user_id',
        "Purchase Orders"
    )
    sales_orders_user_ids = fields.Many2many(
        'res.users',
        'res_company_users_sales_orders',
        'company_id', 'user_id',
        "Sales Orders"
    )
