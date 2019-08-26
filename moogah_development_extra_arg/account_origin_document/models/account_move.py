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

class AccountMove(models.Model):
    _inherit = "account.move"

    type_document = fields.Selection([('account_invoice_v', 'Vendor Bills'),
                                       ('account_invoice_rv', 'Refund Vendor Bills'),
                                       ('account_invoice_c', 'Customer Invoices'),
                                       ('account_invoice_rc', 'Refund Customer Invoices'),
                                       ('account_payment', 'Payment'),
                                       ('account_payment_ich', 'Issue Checks'),
                                       ('account_payment_tch', 'Third Checks'),
                                       ('account_payment_ci', 'Cash In'),
                                       ('account_payment_co', 'Cash Out'),
                                       ('stock_move', 'Stock Pickings'),
                                       ('no_reference', 'Not origin document')], 'Type Document', size=86,
                                      default='no_reference')
    origin_document = fields.Char(u'Origin Document', size=255)
    document_id = fields.Integer(u'Id Document')

    @api.multi
    def action_open_origin_document(self):
        for rec in self:
            if rec.type_document != 'no_reference':
                self.ensure_one()
                if rec.type_document == 'account_invoice_v' or rec.type_document == 'account_invoice_rv':
                    action = self.env.ref('account.action_invoice_tree2').read()[0]
                    form_view_id = self.env.ref('account.invoice_supplier_form').id
                elif rec.type_document == 'account_invoice_c' or rec.type_document == 'account_invoice_rc':
                    action = self.env.ref('account.action_invoice_tree1').read()[0]
                    form_view_id = self.env.ref('account.invoice_form').id
                elif rec.type_document == 'account_payment':
                    action = self.env.ref('account_payment_group.action_account_payments_group_payable').read()[0]
                    form_view_id = self.env.ref('account_payment_group.view_account_payment_group_form').id
                elif rec.type_document == 'account_payment_ich':
                    action = self.env.ref('account_check.action_issue_check').read()[0]
                    form_view_id = self.env.ref('account_check.view_account_check_form').id
                elif rec.type_document == 'account_payment_tch':
                    action = self.env.ref('account_check.action_third_check').read()[0]
                    form_view_id = self.env.ref('account_check.view_account_check_form').id
                elif rec.type_document == 'account_payment_ci':
                    action = self.env.ref('vitt_cashin_cashout.action_cash_in').read()[0]
                    form_view_id = self.env.ref('vitt_cashin_cashout.account_cash_inout_view_form').id
                elif rec.type_document == 'account_payment_co':
                    action = self.env.ref('vitt_cashin_cashout.action_cash_out').read()[0]
                    form_view_id = self.env.ref('vitt_cashin_cashout.account_cash_inout_view_form').id
                elif rec.type_document == 'stock_move':
                    action = self.env.ref('stock.action_picking_tree_all').read()[0]
                    form_view_id = self.env.ref('stock.view_picking_form').id

                action['views'] = [(form_view_id, 'form')]
                action['res_id'] = rec.document_id
                action.pop('target', None)
                return action
        return True

