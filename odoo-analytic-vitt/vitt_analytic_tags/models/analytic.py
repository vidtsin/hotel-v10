# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import models, api, fields, _
from odoo.exceptions import ValidationError


class AccountAnalyticTag(models.Model):
    _inherit = 'account.analytic.tag'
    _order = "code"

    company_id = fields.Many2one('res.company', string='Company', required=False, default=lambda self: self.env.user.company_id)
    code = fields.Char(string='Code')
    required_accounts_ids = fields.One2many('account.analytic.dimension.accounts', related='analytic_dimension_id.required_accounts_ids')
    parent_tag_id = fields.Many2one('account.analytic.tag', string='Parent Tag')
    active = fields.Boolean(string='Active', default=True)

    @api.multi
    @api.model
    def name_get(self):
        res = []
        for tag in self:
            name = tag.name
            if tag.code:
                name = '[%s] %s' % (tag.code, name)
            if tag.analytic_dimension_id:
                name = '%s - %s' % (name, tag.analytic_dimension_id.name)

            res.append((tag.id, name))

        return res

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            dimensions = self.env['account.analytic.dimension'].search([('name', 'ilike', name)]).mapped('id')
            tags_by_name = self.search(['|', ('name', operator, name), ('code', operator, name)]).mapped('id')
            domain = ['|', ('id', 'in', tags_by_name), ('analytic_dimension_id', 'in', dimensions)]

        tags = self.search(domain, limit=limit)
        return tags.name_get()

    def _set_tags(self, tags, new_tags):
        res = tags

        if not new_tags:
            return

        parent_tags = self._get_parent_tags(new_tags)
        ids_tags = tags.mapped('id')
        ids_parent_tags = parent_tags.mapped('id')
        tags_to_add = new_tags.filtered(lambda r: r.id not in ids_tags + ids_parent_tags) + parent_tags  # 'tags_to_add' are the tags not found in 'tags'
        for tag in tags_to_add:
            res |= tag

        return res

    def _get_parent_tags(self, tags):
        res = tags
        if not tags:
            return res

        for tag in tags:
            parent_tag = tag.parent_tag_id
            if parent_tag:
                while parent_tag:
                    res |= parent_tag
                    parent_tag = parent_tag.parent_tag_id

        return res


class AccountAnalyticDimension(models.Model):
    _inherit = 'account.analytic.dimension'

    required_accounts_ids = fields.One2many('account.analytic.dimension.accounts', 'analytic_dimension_id', string='Required in Accounts')


class AccountAnalyticDimensionAccounts(models.Model):
    _name = 'account.analytic.dimension.accounts'
    # Account lines

    analytic_dimension_id = fields.Many2one('account.analytic.dimension', string='Dimension')
    account_id = fields.Many2one('account.account', string='Account')
    name = fields.Char(related='account_id.name', string='Name')

    _sql_constraints = [
        ('account_dimension_uniq', 'unique (analytic_dimension_id, account_id)', 'The account must be unique per Dimension!')
    ]

    def _exist_dimension_in_account(self, account=None, analytic_dimension=None):
        for dimension in account.analytic_dimension_ids:
            if dimension.id == analytic_dimension.id:
                return True
        return False

    def _add_dimension_to_account(self, account_id=None, analytic_dimension_id=None):
        if (not account_id) or (not analytic_dimension_id):
            return

        account = self.env['account.account'].search([('id', '=', account_id)], limit=1)
        analytic_dimension = self.env['account.analytic.dimension'].search([('id', '=', account_id)])
        account_dimensions = self.env['account.account.analytic.dimension']
        if not(self._exist_dimension_in_account(account, analytic_dimension)):
            account.analytic_dimension_ids += account_dimensions.create({'account_id': account_id, 'analytic_dimension_id': analytic_dimension_id})

    def _remove_dimension_of_account(self, account_id=None, analytic_dimension_id=None):
        if (not account_id) or (not analytic_dimension_id):
            return

        domain = [('account_id', '=', account_id.id), ('analytic_dimension_id', '=', analytic_dimension_id.id), ]
        account_dimensions = self.env['account.account.analytic.dimension'].search(domain)

        if not account_dimensions:
            return

        for acc_dimension in account_dimensions:
            acc_dimension.unlink()

    def write(self, vals):
        self._add_dimension_to_account(vals.get('account_id'), vals.get('analytic_dimension_id'))
        return super(AccountAnalyticDimensionAccounts, self).write(vals)

    def create(self, vals):
        self._add_dimension_to_account(vals.get('account_id'), vals.get('analytic_dimension_id'))
        return super(AccountAnalyticDimensionAccounts, self).create(vals)

    @api.multi
    def unlink(self):
        for dimension_account in self:
            dimension_account._remove_dimension_of_account(dimension_account.account_id, dimension_account.analytic_dimension_id)
        return super(AccountAnalyticDimensionAccounts, self).unlink()
