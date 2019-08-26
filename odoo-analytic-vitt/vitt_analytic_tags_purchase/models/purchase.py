# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import models, api, fields, _
from odoo.exceptions import ValidationError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')

    @api.multi
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        res = super(PurchaseOrder, self).onchange_partner_id()
        self._add_analytic_tags(self.partner_id.supplier_analytic_tag_ids)
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
            for line in self.order_line:
                tags_rows = analytic_tags + line.analytic_tag_ids if tags else line.analytic_tag_ids

                line._add_analytic_tags(tags_rows)

    @api.multi
    @api.constrains('state')
    def _check_analytic_tags_account(self):
        for order in self:
            for line in order.order_line:
                line._check_analytic_tags_account()


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    account_id = fields.Many2one('account.account', string='Account', ondelete='cascade', domain=[('deprecated', '=', False)])

    @api.constrains('analytic_tag_ids')
    def _check_analytic_tags_account(self):
        if not self.account_id:
            return True

        if self.order_id.state not in ['draft', 'cancel']:
            check_account_tag_control = self.account_id._check_account_tag_control(self.analytic_tag_ids)
            if not check_account_tag_control:
                return False

    @api.multi
    @api.onchange('product_id')
    def onchange_product_id(self):
        res = super(PurchaseOrderLine, self).onchange_product_id()
        if self.product_id:
            self.account_id = self.product_id.product_tmpl_id._get_product_accounts()['expense']
        self._add_analytic_tags(self.product_id.supplier_analytic_tag_ids + self.product_id.categ_id.supplier_analytic_tag_ids)

        return res

    def _add_analytic_tags(self, tags):
        new_tags = tags
        tags_ids = self.analytic_tag_ids
        if self.order_id.company_id.analytic_tags_to_rows and self.order_id.analytic_tag_ids:
            new_tags += self.order_id.analytic_tag_ids
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
        return super(PurchaseOrderLine, self).write(vals)

    def create(self, vals):
        vals = self._update_vals(vals)
        return super(PurchaseOrderLine, self).create(vals)
