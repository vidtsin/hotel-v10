# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import models, api, fields, _
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')

    @api.multi
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        res = super(SaleOrder, self).onchange_partner_id()
        partner = self.partner_id
        tags = partner.analytic_tag_ids

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
            for line in self.order_line:
                tags_rows = analytic_tags + line.analytic_tag_ids if tags else line.analytic_tag_ids

                line._add_analytic_tags(tags_rows)

    @api.multi
    @api.constrains('state')
    def _check_analytic_tags_account(self):
        for order in self:
            for line in order.order_line:
                line._check_analytic_tags_account()

    @api.multi
    def _prepare_invoice(self):
        self.ensure_one()
        res = super(SaleOrder, self)._prepare_invoice()
        res.update({
            'analytic_tag_ids': [(6, 0, self.analytic_tag_ids.ids)]
        })

        return res


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

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
    def product_id_change(self):
        res = super(SaleOrderLine, self).product_id_change()
        if self.product_id:
            self.account_id = self.product_id.product_tmpl_id._get_product_accounts()['income']
        self._add_analytic_tags(self.product_id.analytic_tag_ids + self.product_id.categ_id.analytic_tag_ids)

        return res

    def _add_analytic_tags(self, tags):
        new_tags = tags
        tags_ids = self.analytic_tag_ids
        if self.order_id.company_id.analytic_tags_to_rows and self.order_id.analytic_tag_ids:
            new_tags += self.order_id.analytic_tag_ids
        analytic_tags = self.analytic_tag_ids._set_tags(tags=tags_ids, new_tags=new_tags)

        self.analytic_tag_ids = analytic_tags

    @api.multi
    def _prepare_invoice_line(self, qty):
        self.ensure_one()
        res = super(SaleOrderLine, self)._prepare_invoice_line(qty)
        if self.account_id:
            res['account_id'] = self.account_id.id
        return res

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
        return super(SaleOrderLine, self).write(vals)

    def create(self, vals):
        vals = self._update_vals(vals)
        return super(SaleOrderLine, self).create(vals)
