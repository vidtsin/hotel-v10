from odoo import models, fields, api, _
from odoo.exceptions import ValidationError,UserError
import odoo.addons.decimal_precision as dp

class AccountCashInOut(models.Model):
    _inherit = "account.cash.inout"

    @api.multi
    def validate_cash(self):
        result = super(AccountCashInOut, self).validate_cash()
        for cash in self:
            move = cash.move_id
            move_vals = {}
            if cash.type == 'cash_in':
                move_vals['origin_document'] = cash.display_name
                move_vals['type_document'] = 'account_payment_ci'
                move_vals['document_id'] = cash.id
            elif cash.type == 'cash_out':
                move_vals['origin_document'] = cash.display_name
                move_vals['type_document'] = 'account_payment_co'
                move_vals['document_id'] = cash.id
            move.write(move_vals)
        return result

