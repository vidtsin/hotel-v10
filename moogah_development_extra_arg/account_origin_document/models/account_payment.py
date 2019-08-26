# -*- coding: utf-8 -*-
###############################################################################
#
#   account_origin_document for Odoo
#   Copyright (C) 2004-today OpenERP SA (<http://www.openerp.com>)
#   Copyright (C) 2017-today Troova Software Development Group (troovacomercial@gmail.com).
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as
#   published by the Free Software Foundation, either version 3 of the
#   License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

from odoo import api, exceptions, fields, models, _
from odoo.exceptions import UserError

class AccountPayment(models.Model):
    _inherit = "account.payment"

    def _get_move_vals(self, journal=None):
        """ Return dict to create the payment move
        """
        vals = super(AccountPayment, self)._get_move_vals()
        if self.partner_type == 'customer' or self.partner_type == 'supplier':
            vals['origin_document'] = self.display_name
            vals['type_document'] = 'account_payment'
            vals['document_id'] = self.payment_group_id.id
        return vals

class AccountPaymentGroup(models.Model):
    _inherit = "account.payment.group"

    def post(self):
        res = super(AccountPaymentGroup, self).post()
        for rec in self:
            moves = self.env['account.move'].search([('document_id', '=', rec.id)])
            moves.write({'origin_document': rec.display_name})
        return res

