# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountReportType(models.Model):
    _inherit = "account.report.type"

    account = fields.Boolean('Reports enable the account filter', default=False)
    balance = fields.Boolean('Reports enable the balance filter', default=False)
    dimension = fields.Boolean('Reports enable the dimension filter', default=False)

