# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError


class AuthorizationsConfigSettings(models.TransientModel):
    _name = 'authorizations.config.settings'
    _inherit = 'res.config.settings'

    def _default_company(self):
        return self.env.ref('base.main_company')

    company_id = fields.Many2one('res.company', string='Company',
                                 required=True,
                                 default=_default_company)
    purchase_invoices = fields.Float(related='company_id.purchase_invoices')
    sales_invoices = fields.Float(related='company_id.sales_invoices')
    purchase_orders = fields.Float(related='company_id.purchase_orders')
    sales_orders = fields.Float(related='company_id.sales_orders')

    purchase_invoices_user_ids = fields.Many2many(
        'res.users',
        related='company_id.purchase_invoices_user_ids'
    )
    sales_invoices_user_ids = fields.Many2many(
        'res.users',
        related='company_id.sales_invoices_user_ids'
    )
    purchase_orders_user_ids = fields.Many2many(
        'res.users',
        related='company_id.purchase_orders_user_ids'
    )
    sales_orders_user_ids = fields.Many2many(
        'res.users',
        related='company_id.sales_orders_user_ids'
    )

    def _update_dependences(self):
        domain = [('state', 'in', ['draft', 'sent'])]
        self.env['sale.order'].search(domain)._compute_to_approve()

        self.env['purchase.order'].search(domain)._compute_to_approve()

        domain = [('state', 'in', ['draft'])]
        self.env['account.invoice'].search(domain)._compute_to_approve()

    @api.model
    def create(self, vals):
        resp = super(AuthorizationsConfigSettings, self).create(vals)
        self._update_dependences()
        return resp

    @api.multi
    def write(self, vals):
        resp = super(AuthorizationsConfigSettings, self).write(vals)
        self._update_dependences()
        return resp