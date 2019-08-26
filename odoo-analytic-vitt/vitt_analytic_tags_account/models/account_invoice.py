# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import models, api, fields, _
from odoo.exceptions import ValidationError

TYPE_IN = ['in_invoice', 'in_refund']
TYPE_OUT = ['out_invoice', 'out_refund']


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')

    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        res = super(AccountInvoice, self)._onchange_partner_id()
        partner = self.partner_id
        tags = partner.analytic_tag_ids if self.type in TYPE_OUT else partner.supplier_analytic_tag_ids

        self._add_analytic_tags(tags)
        return res

    @api.onchange('analytic_tag_ids')
    def _onchange_analytic_tag_ids(self):
        self._add_analytic_tags(self.analytic_tag_ids)

    def _add_analytic_tags(self, tags):
        new_tags = tags
        tags_ids = self.analytic_tag_ids
        analytic_tags = self.analytic_tag_ids._set_tags(tags=tags_ids, new_tags=new_tags)
        self.analytic_tag_ids = analytic_tags

        if self.company_id.analytic_tags_to_rows:  # update rows with the header tags
            for line in self.invoice_line_ids:
                tags_rows = analytic_tags + line.analytic_tag_ids if tags else line.analytic_tag_ids

                line._add_analytic_tags(tags_rows)

    @api.multi
    def action_invoice_open(self):
        res = super(AccountInvoice, self).action_invoice_open()
        for inv in self:
            if inv.move_id and inv.analytic_tag_ids:
                inv.analytic_tag_ids = inv.analytic_tag_ids._set_tags(tags=inv.analytic_tag_ids, new_tags=inv.analytic_tag_ids)
                for move_line in inv.move_id.line_ids:
                    if move_line.account_id.id == inv.account_id.id:
                        analytic_tags = inv.analytic_tag_ids._set_tags(tags=move_line.analytic_tag_ids, new_tags=inv.analytic_tag_ids)
                        move_line.write({'analytic_tag_ids': [(6, 0, analytic_tags.ids)]})

        return res

    @api.multi
    @api.constrains('state')
    def _check_analytic_tags_account(self):
        for invoice in self:
            for line in invoice.invoice_line_ids:
                line._check_analytic_tags_account()


class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    @api.constrains('analytic_tag_ids')
    def _check_analytic_tags_account(self):
        if not self.account_id:
            return True

        if self.invoice_id.state not in ['draft', 'cancel', 'proforma', 'proforma2']:
            check_account_tag_control = self.account_id._check_account_tag_control(self.analytic_tag_ids)
            if not check_account_tag_control:
                return False

    @api.onchange('product_id')
    def _onchange_product_id(self):
        res = super(AccountInvoiceLine, self)._onchange_product_id()
        tags = self.product_id.analytic_tag_ids + self.product_id.categ_id.analytic_tag_ids
        if self.invoice_id.type in TYPE_IN:
            tags = self.product_id.supplier_analytic_tag_ids + self.product_id.categ_id.supplier_analytic_tag_ids

        self._add_analytic_tags(tags)

        return res

    def _add_analytic_tags(self, tags):
        new_tags = tags
        tags_ids = self.analytic_tag_ids
        if self.invoice_id.company_id.analytic_tags_to_rows and self.invoice_id.analytic_tag_ids:
            new_tags += self.invoice_id.analytic_tag_ids
        analytic_tags = self.analytic_tag_ids._set_tags(tags=tags_ids, new_tags=new_tags)

        self.analytic_tag_ids = analytic_tags

    def _update_vals(self, vals):
        try:
            ids = vals.get('analytic_tag_ids')[0][2]
            new_tags = tags_ids = self.env['account.analytic.tag'].browse(ids)
            analytic_tags = self.analytic_tag_ids._set_tags(tags=tags_ids, new_tags=new_tags)
            if analytic_tags:
                vals.update({'analytic_tag_ids': [(6, 0, analytic_tags.ids)]})
        except:
            return vals

        return vals

    def write(self, vals):
        vals = self._update_vals(vals)
        return super(AccountInvoiceLine, self).write(vals)

    def create(self, vals):
        vals = self._update_vals(vals)
        return super(AccountInvoiceLine, self).create(vals)
