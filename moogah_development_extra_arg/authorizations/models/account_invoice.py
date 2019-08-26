# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    approved = fields.Boolean("Approved", readonly=True, copy=False)
    approved_uid = fields.Many2one('res.users', 'Authorizer', readonly=True,
                                   copy=False)
    approved_datetime = fields.Datetime('Date', readonly=True, copy=False)
    approved_time = fields.Datetime('Time', compute='_compute_approved_time')
    to_approve = fields.Boolean("To Approve", compute='_compute_to_approve',
                                search='_search_to_approve')
    can_approve = fields.Boolean("Can Approve", compute='_compute_can_approve')

    @api.one
    def _compute_approved_time(self):
        self.approved_time = self.approved_datetime

    @api.multi
    @api.depends('type', 'amount_total', 'approved')
    def _compute_to_approve(self):
        main_company = self.env.ref('base.main_company')
        for rec in self:
            if rec.type in ['in_invoice', 'in_refund']:
                min = main_company.purchase_invoices
            else:
                min = main_company.sales_invoices
            rec.to_approve = rec.amount_total >= min and not rec.approved

    @api.multi
    def _search_to_approve(self, operator, value):
        main_company = self.env.ref('base.main_company')
        min = main_company.sales_invoices
        records = self.env['account.invoice'].sudo().search([
            ('type', 'not in', ['in_invoice', 'in_refund']),
            ('amount_total', '>=', min), ('approved', '=', False)])
        min = main_company.purchase_invoices
        purchase_records = self.env['account.invoice'].sudo().search([
            ('type', 'in', ['in_invoice', 'in_refund']),
            ('amount_total', '>=', min), ('approved', '=', False)])
        records |= purchase_records
        return [('id', 'in', records.ids)]

    @api.multi
    @api.depends('type', 'to_approve')
    def _compute_can_approve(self):
        main_company = self.env.ref('base.main_company')
        for rec in self:
            if rec.type in ['in_invoice', 'in_refund']:
                users = main_company.purchase_invoices_user_ids
            else:
                users = main_company.sales_invoices_user_ids
            rec.can_approve = rec.to_approve and self.env.user in users

    @api.multi
    def action_approve(self):
        self.ensure_one()
        if not self.can_approve:
            raise UserError(_("The approval cannot be performed"))
        self.write({
            'approved': True,
            'approved_uid': self.env.user.id,
            'approved_datetime': fields.Datetime.now()
        })

    @api.multi
    def action_invoice_open(self):
        self.write({'approved': True})
        return super(AccountInvoice, self).action_invoice_open()
