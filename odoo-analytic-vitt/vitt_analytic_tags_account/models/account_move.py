# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import models, api, fields, _
from odoo.exceptions import ValidationError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.constrains('analytic_tag_ids')
    def _check_analytic_tags_move_line(self):
        if not self.account_id:
            return True

        check_account_tag_control = self.account_id._check_account_tag_control(self.analytic_tag_ids)
        if not check_account_tag_control:
            return False
