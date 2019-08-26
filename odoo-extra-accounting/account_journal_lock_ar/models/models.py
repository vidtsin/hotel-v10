from odoo import api, fields, models

class ResUsers(models.Model):
    _inherit = 'res.users'

    lock_date_bypass = fields.Boolean(string="Permitir grabar con bloqueo de fechas")

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    @api.model
    def _can_bypass_journal_lock_date(self):
        return self.env.user.lock_date_bypass

class AccountJournalLock(models.TransientModel):
    _name = 'account.journal.lock'

    lock_date = fields.Date(string="Nueva Fecha")

    def change_lock_date(self):
        active_ids = self.env.context.get('active_ids', [])
        journals = self.env['account.journal'].browse(active_ids)
        for journal in journals:
            journal.journal_lock_date = self.lock_date

