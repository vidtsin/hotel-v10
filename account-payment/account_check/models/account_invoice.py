from odoo import fields, models, _, api
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    @api.multi
    def action_invoice_open(self):
        super(AccountInvoice, self).action_invoice_open()
        for rec in self:
            inv = rec.env['account.invoice']
            inv += rec
            check_op = rec.env['account.check.operation'].search([('owner_id','=',inv.id),('owner_model','=',inv._name)],limit=1)
            if check_op:
                check_op.write({'move_id':self.move_id.id})

