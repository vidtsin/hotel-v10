# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import models, api, fields, _
from odoo.exceptions import ValidationError


class AccountAccount(models.Model):
    _inherit = 'account.account'

    analytic_dimension_ids = fields.One2many('account.account.analytic.dimension', 'account_id', string='Dimensions')

    def _check_account_tag_control(self, tags=None):
        if not self.analytic_dimension_ids:
            return True

        dimensions_not_found = []
        for lines in self.analytic_dimension_ids:
            foundf = False
            for tag in tags:
                if tag.analytic_dimension_id.id == lines.analytic_dimension_id.id:
                    foundf = True
                    break

            if not foundf:
                dimensions_not_found.append(lines.name)

        if dimensions_not_found:
            msgstr = _("The Account '%s' requires a tag of dimension; %s" % (self.name, ', '.join(dimensions_not_found)))
            raise ValidationError(msgstr)
            return False

        return True


class AccountAccountAnalyticDimension(models.Model):
    _name = 'account.account.analytic.dimension'
    # Dimensions lines

    account_id = fields.Many2one('account.account', string='Account', ondelete='cascade')
    analytic_dimension_id = fields.Many2one('account.analytic.dimension', string='Dimension', ondelete='cascade')
    name = fields.Char(string='Name', related='analytic_dimension_id.name')
