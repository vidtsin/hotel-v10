# -*- coding: utf-8 -*-
# © 2016 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import models, api, fields, _
from openerp.exceptions import ValidationError


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    open_move_line_ids = fields.One2many(
        'account.move.line',
        compute='_compute_open_move_lines'
    )
    nc_ref_id = fields.Integer(string='Original Document', translate=True)

    @api.multi
    def _get_tax_factor(self):
        self.ensure_one()
        return (self.amount_total and (self.amount_untaxed / self.amount_total) or 1.0)

    @api.multi
    def _compute_open_move_lines(self):
        for rec in self:
            rec.open_move_line_ids = rec.move_id.line_ids.filtered(
                lambda r: not r.reconciled and r.account_id.internal_type in (
                    'payable', 'receivable'))

    @api.multi
    def action_account_invoice_payment_group(self):
        self.ensure_one()
        if self.state != 'open':
            raise ValidationError(_(
                'You can only register payment if invoice is open'))
        # target = 'new'
        # if self.company_id.double_validation:
        #     target = 'current'
        return {
            'name': _('Register Payment'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.payment.group',
            'view_id': False,
            'target': 'current',
            # 'target': target,
            'type': 'ir.actions.act_window',
            # 'domain': [('id', 'in', aml.ids)],
            'context': {
                'to_pay_move_line_ids': self.open_move_line_ids.ids,
                'pop_up': True,
                'default_company_id': self.company_id.id,
            },
        }

    @api.multi
    def action_invoice_open(self):
        res = super(AccountInvoice, self).action_invoice_open()
        for inv in self:
            if inv.nc_ref_id != False:
                domain = [('account_id', '=', inv.account_id.id),
                          ('partner_id', '=', inv.env['res.partner']._find_accounting_partner(inv.partner_id).id),
                          ('reconciled', '=', False), ('amount_residual', '!=', 0.0), ('invoice_id','=', inv.nc_ref_id)]
                lines = self.env['account.move.line'].search(domain)
                paym = inv.assign_outstanding_credit(lines.id)
        return res

class AccountInvoiceRefund(models.TransientModel):
    _inherit = "account.invoice.refund"

    def invoice_refund(self):
        res = super(AccountInvoiceRefund, self).invoice_refund()
        invoice_id = self.env['account.invoice'].browse(self._context.get('active_id', False))
        nc_id = res['domain'][1][2]
        nc = self.env['account.invoice'].search([('id','=',int(nc_id[0]))])
        nc.write({'nc_ref_id':invoice_id.id})
        if len(nc_id) > 1:
            new_inv = self.env['account.invoice'].search([('id', '=', int(nc_id[1]))])
            new_inv.journal_document_type_id = (
                new_inv._get_available_journal_document_types(
                    new_inv.journal_id, new_inv.type, new_inv.partner_id
                ).get('journal_document_type'))
        return res
