from odoo import models, api, _, fields

class account_journal(models.Model):
    _inherit = "account.journal"

    @api.multi
    def action_open_reconcile(self):
        # if self.type in ['bank', 'cash']:
        #     # Open reconciliation view for bank statements belonging to this journal
        #     bank_stmt = self.env['account.bank.statement'].search([('journal_id', 'in', self.ids)])
        #     return {
        #         'type': 'ir.actions.client',
        #         'tag': 'bank_statement_reconciliation_view',
        #         'context': {'statement_ids': bank_stmt.ids, 'company_ids': self.mapped('company_id').ids},
        #     }
        # else:
        if True:
            # Open reconciliation view for customers/suppliers
            action_context = {'show_mode_selector': False, 'company_ids': self.mapped('company_id').ids}
            if self.type == 'sale':
                action_context.update({'mode': 'customers'})
            elif self.type == 'purchase':
                action_context.update({'mode': 'suppliers'})
            return {
                'type': 'ir.actions.client',
                'tag': 'manual_reconciliation_view',
                'context': action_context,
            }
