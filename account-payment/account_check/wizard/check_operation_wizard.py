# -*- coding: utf-8 -*-
from odoo.exceptions import Warning, UserError
from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)


class account_check_wizard(models.TransientModel):
    _name = 'account.check.wizard'

    @api.model
    def _get_company_id(self):
        active_ids = self._context.get('active_ids', [])
        checks = self.env['account.check'].browse(active_ids)
        company_ids = [x.company_id.id for x in checks]
        if len(set(company_ids)) > 1:
            raise Warning(_('All checks must be from the same company!'))
        return self.env['res.company'].search(
            [('id', 'in', company_ids)], limit=1)
    company_currency_id = fields.Many2one(
        related='company_id.currency_id',
        readonly=True,
    )
    journal_id = fields.Many2one(
        'account.journal',
        'Journal',
        domain="[('company_id','=',company_id), "
        "('type', 'in', ['cash', 'bank']), "
        "('outbound_payment_method_ids', 'not in', [ 7, 8]), "
        "('inbound_payment_method_ids', 'not in', [3, 6])]"
    )
    account_id = fields.Many2one(
        'account.account',
        'Account',
        related='journal_id.default_debit_account_id',
        store=True,
#        domain="[('company_id','=',company_id), "
#        "('type', 'in', ('other', 'liquidity'))]",
#        readonly=True
    )
    exp_account_id = fields.Many2one(
        'account.account',
        'Account',
        related='journal_id.default_debit_account_id',
        store=True,
#        domain="[('company_id','=',company_id), "
#        "('type', 'in', ('other', 'liquidity'))]",
#        readonly=True
    )
    exp_amount = fields.Monetary('Amount',
        # related='move_line_id.balance',
        currency_field='company_currency_id',
    )
    exp_type = fields.Selection([('1', 'No Expenses'), ('2', 'Internal Expenses'), ('3', 'Expenses invoiced')], 'Type',
    )
    date = fields.Date(
        'Date', required=True, default=fields.Date.context_today
    )
    action_type = fields.Char(
        'Action type passed on the context', required=True,
    )
    company_id = fields.Many2one(
        'res.company',
        'Company',
        required=True,
        default=_get_company_id,
    )
            
    @api.multi
    def action_confirm(self):
        self.ensure_one()

        print self.action_type
        for check in self.env['account.check'].browse(self._context.get('active_ids', [])):
            if self.action_type == 'deposit':
                self.bank_deposited(check, self.journal_id, self.date)
            elif self.action_type == 'bank_reject':
                self.bank_rejected(check, self.date)
            elif self.action_type == 'supplier_reject':
                self.supplier_reject(check, self.date)
            elif self.action_type == 'return':
                self.returned(check, self.date)
            elif self.action_type == 'revert_return':
                self.revert_return(check, self.date)
            elif self.action_type == 'claim':
                self.claim(check, self.date, self.exp_account_id, self.exp_amount, self.exp_type)
            elif self.action_type == 'bank_debit':
                self.bank_debit(check, self.date)
            elif self.action_type == 'cancel_claim':
                self.cancel_claim(check, self.date, self.exp_account_id, self.exp_amount, self.exp_type)
            elif self.action_type == 'cancel_claim_cust':
                self.cancel_claim_cust(check, self.date, self.exp_account_id, self.exp_amount, self.exp_type)

                
    @api.multi
    def bank_debit(self, check, date):
        self.ensure_one()
        if check.state in ['handed']:
            vals = check.get_bank_vals(
                'bank_debit', check.checkbook_id.debit_journal_id, date)
            move = self.env['account.move'].create(vals)
            move.post()
            check._add_operation('debited', move, None, None, move.id)
                
    @api.multi
    def returned(self,check, date):
        self.ensure_one()
        if check.state in ['holding'] or check.state in ['handed']:
            vals = check.get_bank_vals('return_check', check.journal_id, date)
            move = self.env['account.move'].create(vals)
            move.post()            
            check._add_operation('returned', move, None, None, move.id)
            
            
    @api.multi
    def revert_return(self,check, date):
        self.ensure_one()
        if check.state in ['returned']:
            vals = check.get_bank_vals('revert_return', check.journal_id, date)
            move = self.env['account.move'].create(vals)
            move.post()
            if check.type == 'issue_check':
                self.write({'state': 'handed'})
                check._add_operation('handed', move, None, None, move.id)
            else:
                check._add_operation('holding', move, None, None, move.id)
            
    @api.multi
    def bank_deposited(self, check, journal_id, date):
        self.ensure_one()
        if check.state in ['holding']:
            vals = check.get_bank_vals(
                'bank_deposited', journal_id, date)
            move = self.env['account.move'].create(vals)
            move.post()
            check._add_operation('deposited', move, None, None, move.id)
            
            
    @api.multi
    def claim(self, check, date, account=None, amount=None, exp_type=None):
        self.ensure_one()
        last_operation = check._get_last_operation().operation
        if check.type == 'third_check':
            if last_operation == 'returned':
                account_company = self.company_id._get_check_account('third_party_cancelled')
            else: 
                account_company = self.company_id._get_check_account('rejected')
            partner_type = 'customer'
        else:
            #if last_operation == 'returned':
            account_company = self.company_id._get_check_account('own_check_rejected')
            partner_type = 'supplier'    
        try:
            operation = check._get_operation('reclaimed')
            operation.origin.action_invoice_cancel()
        except:
            pass
            #raise UserError(_('Can\'t discard last Debit Note!'))

        if check.type == 'issue_check':
            operation = check._get_operation('rejected')
            if operation.owner_model == 'account.invoice':
                inv = self.env['account.invoice'].search([('id', '=', operation.owner_id)])
                if inv.state not in ['paid']:
                    raise UserError(_("Invoice must be in paid state in order to be canceled on claim to supplier"))

        if exp_type == '3':
            if amount <= 0:
                raise UserError(_('You can\'t claim with Zero Amount!'))

        return check.action_create_debit_note('reclaimed', partner_type, check.partner_id, account, amount, account_company)


    @api.multi
    def cancel_claim_cust(self, check, date, account=None, amount=None, exp_type=None):
        self.ensure_one()
        last_operation = check._get_last_operation().operation
        if check.type == 'third_check':
            if last_operation == 'returned':
                account_company = self.company_id._get_check_account('third_party_cancelled')
            else:
                account_company = self.company_id._get_check_account('rejected')
            partner_type = 'customer'
        else:
            raise UserError(_("not implemented yet"))
        if check.type == 'third_check':
            operation = check._get_operation('reclaimed')
            #if operation.origin.filtered(lambda inv: inv.state not in ['open']):
            inv = self.env['account.invoice'].search([('id','=', operation.owner_id)])
            if not (inv.state in ['open'] and inv.residual == inv.amount_total):
                raise UserError(_("Invoice must be fully open state in order to be canceled on cancel claim"))
        if check.state in ['rejected', 'returned', 'reclaimed']:
            if exp_type == '3':
                if amount <= 0:
                    raise UserError(_('You can\'t claim with Zero Amount!'))
            if last_operation == 'returned':
                return check.action_create_debit_note('returned', partner_type, check.partner_id, account, amount,
                                                      account_company,credit=True)
            else:
                return check.action_create_debit_note('rejected', partner_type, check.partner_id, account, amount,
                                                      account_company,credit=True)


    @api.multi
    def cancel_claim(self, check, date, account=None, amount=None, exp_type=None):
        self.ensure_one()
        last_operation = check._get_last_operation().operation
        if check.type == 'third_check':
            raise UserError(_("not implemented yet"))
        else:
            if last_operation == 'returned':
                account_company = self.company_id._get_check_account('returned')
            else:
                account_company = self.company_id._get_check_account('rejected')
            partner_type = 'supplier'
        if check.type == 'issue_check':
            operation = check._get_operation('reclaimed')
            inv = self.env['account.invoice'].search([('id','=', operation.owner_id)])
            if not (inv.state in ['open'] and inv.residual == inv.amount_total):
                raise UserError(_("Invoice must be fully open state in order to be canceled on cancel claim"))
        if check.state in ['rejected', 'returned', 'reclaimed']:
            if exp_type == '3':
                if amount <= 0:
                    raise UserError(_('You can\'t claim with Zero Amount!'))
            print 'last_operation ', last_operation
            if last_operation == 'returned':
                return check.action_create_debit_note('returned', partner_type, check.partner_id, account, amount,
                                                      account_company,credit=True)
            else:
                return check.action_create_debit_note('rejected', partner_type, check.partner_id, account, amount,
                                                      account_company,credit=True)

    @api.multi
    def bank_rejected(self, check, date):
        self.ensure_one()
        #if check.state in ['deposited']:
        try:
            operation = check._get_operation('deposited')
            journal_id = operation.origin.journal_id
        except:
            journal_id = None
        #check.write({'prev_state':check.state})
        if check.state in ['deposited']:
            vals = check.get_bank_vals('bank_reject', journal_id, date)
            move = self.env['account.move'].create(vals)
            move.post()
            check._add_operation('rejected', move, None, None, move.id)
        if check.state in ['delivered']:
            vals = check.get_bank_vals('deliver_reject', None, date)
            move = self.env['account.move'].create(vals)
            move.post()
            check._add_operation('rejected', move, None, None, move.id)
        elif check.state in ['handed']:
            #operation = check._get_operation('handed')
            #journal_id = operation.origin.journal_id
            vals = check.get_bank_vals('supplier_reject',None, date)
            move = self.env['account.move'].create(vals)
            move.post()
            check._add_operation('rejected', move, None, None, move.id)
            
            
    @api.multi
    def supplier_reject(self, check, date):
        self.ensure_one()
        if check.state in ['delivered']:
            try:
                operation = check._get_operation('holding')
                journal_id = operation.origin.journal_id
            except:
                journal_id = None
            vals = check.get_bank_vals(
                'supplier_rejected', journal_id, date)
            move = self.env['account.move'].create(vals)
            move.post()
            check._add_operation('rejected', move, None, None, move.id)
            vals = check.get_bank_vals('bank_reject', journal_id, date)
            move = self.env['account.move'].create(vals)
            move.post()
            check._add_operation('rejected', move, None, None, move.id)


    @api.model
    def default_get(self,fields):
        recs = self.env['account.check.wizard'].search([])
        query = "delete from account_check_wizard"
        self._cr.execute(query, ())
        return super(account_check_wizard, self).default_get(fields)
