# -*- coding: utf-8 -*-
# © 2016 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import models, fields


class ResCompany(models.Model):
    _inherit = "res.company"

    double_validation = fields.Boolean(
        'Double Validation on Payments?',
        translate=True,
        help='Use two steps validation on payments to suppliers'
        # readonly=True,
    )
    arg_sortdate = fields.Boolean(string="Sort Date payments based on Due Date",translate=True)
