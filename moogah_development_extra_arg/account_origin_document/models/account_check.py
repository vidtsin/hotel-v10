from odoo import models, fields, api, _
from odoo.exceptions import ValidationError,UserError
import odoo.addons.decimal_precision as dp

class AccountCheck(models.Model):
    _inherit = "account.check"

    @api.multi
    def _add_operation(self, operation, origin, partner=None, date=False, moveid=None):
        result = super(AccountCheck, self)._add_operation(operation, origin, partner, date, moveid)
        for check in self:
            if moveid:
                move = self.env['account.move'].browse(moveid)
                move_vals = {}
                if check.type == 'issue_check':
                    move_vals['origin_document'] = check.display_name
                    move_vals['type_document'] = 'account_payment_ich'
                    move_vals['document_id'] = check.id
                elif check.type == 'third_check':
                    move_vals['origin_document'] = check.display_name
                    move_vals['type_document'] = 'account_payment_tch'
                    move_vals['document_id'] = check.id
                move.write(move_vals)
        return result

