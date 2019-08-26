# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import models, api, fields, _
from odoo.exceptions import ValidationError


class SaleSubscription(models.Model):
    _inherit = "sale.subscription"

    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')

    @api.multi
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        res = super(SaleSubscription, self).onchange_partner_id()
        partner = self.partner_id
        tags = partner.analytic_tag_ids

        self._add_analytic_tags(tags)
        return res

    @api.onchange('template_id')
    def on_change_template(self):
        super(SaleSubscription, self).on_change_template()
        for line in self.recurring_invoice_line_ids:
            line.onchange_product_id()

    @api.onchange('analytic_tag_ids')
    def _onchange_analytic_tag_ids(self):
        self._add_analytic_tags(self.analytic_tag_ids)

    def _add_analytic_tags(self, tags):
        new_tags = tags
        tags_ids = self.analytic_tag_ids
        analytic_tags = self.analytic_tag_ids._set_tags(tags=tags_ids, new_tags=new_tags)
        self.analytic_tag_ids = analytic_tags

        if self.company_id.analytic_tags_to_rows:  # update rows with the header tags
            for line in self.recurring_invoice_line_ids:
                tags_rows = analytic_tags + line.analytic_tag_ids if tags else line.analytic_tag_ids

                line._add_analytic_tags(tags_rows)

    @api.multi
    @api.constrains('state')
    def _check_analytic_tags_account(self):
        for order in self:
            for line in order.recurring_invoice_line_ids:
                line._check_analytic_tags_account()

    @api.multi
    def _prepare_invoice(self):
        self.ensure_one()
        res = super(SaleSubscription, self)._prepare_invoice()
        if res and self.analytic_tag_ids.ids:
            res.update({'analytic_tag_ids': [(6, 0, self.analytic_tag_ids.ids)]})

        return res

    @api.multi
    def _prepare_invoice_line(self, line, fiscal_position):
        res = super(SaleSubscription, self)._prepare_invoice_line(line, fiscal_position)
        if res and line.analytic_tag_ids:
            res.update({'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)]})
        return res


class SaleSubscriptionLine(models.Model):
    _inherit = "sale.subscription.line"

    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')
    account_id = fields.Many2one('account.account', string='Account', ondelete='cascade', domain=[('deprecated', '=', False)])

    @api.constrains('analytic_tag_ids')
    def _check_analytic_tags_account(self):
        if not self.account_id:
            return True

        if self.analytic_account_id.state not in ['draft', 'close', 'cancel']:
            check_account_tag_control = self.account_id._check_account_tag_control(self.analytic_tag_ids)
            if not check_account_tag_control:
                return False

    @api.onchange('product_id')
    def onchange_product_id(self):
        res = super(SaleSubscriptionLine, self).onchange_product_id()
        if self.product_id:
            self.account_id = self.product_id.product_tmpl_id._get_product_accounts()['income']
        self._add_analytic_tags(self.product_id.analytic_tag_ids)

        return res

    def _add_analytic_tags(self, tags):
        new_tags = tags
        tags_ids = self.analytic_tag_ids
        if self.analytic_account_id.company_id.analytic_tags_to_rows and self.analytic_account_id.analytic_tag_ids:
            new_tags += self.analytic_account_id.analytic_tag_ids
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
        return super(SaleSubscriptionLine, self).write(vals)

    def create(self, vals):
        vals = self._update_vals(vals)
        return super(SaleSubscriptionLine, self).create(vals)
