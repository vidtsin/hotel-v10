from odoo import models, fields, api, _
from odoo.exceptions import ValidationError,UserError
import odoo.addons.decimal_precision as dp

class AccountCheck(models.Model):
    _inherit = 'account.check.operation'

    operation = fields.Selection(selection_add=[('draft', 'Draft')])

class AccountCheck(models.Model):
    _inherit = 'account.check'

    cashin_out_id = fields.Many2one('account.cash.inout',ondelete="set null")
    amount_cash = fields.Float(string="Monto",translate=True)

    @api.model
    def default_get(self, vals):
        res = super(AccountCheck, self).default_get(vals)
        flag = self._context.get('from_cash',False)
        if flag:
            raise UserError(_("Can't Create it from here"))
        return res

    @api.multi
    def unlink(self):
        foundf = True
        for check in self:
            if check.cashin_out_id:
                check.cashin_out_id = False
                foundf = False
        if foundf:
            return super(AccountCheck, self).unlink()


class AccountCashInOut(models.Model):
    #_inherit = "account.check.deposit"
    _name = "account.cash.inout"

    @api.multi
    @api.depends('check_line_ids')
    def _compute_nrofchecks(self):
        self.ensure_one()
        self.number_of_checks = len(self.check_line_ids)

    @api.multi
    @api.depends('check_line_ids','total_amount')
    @api.onchange('check_line_ids','total_amount','journal_id')
    def onchange_compute_amount(self):
        self.ensure_one()
        types = self.journal_id.inbound_payment_method_ids.mapped('code') + self.journal_id.outbound_payment_method_ids.mapped('code')
        if 'issue_check' in types:
            if self.check_line_ids:
                self.total_amount = sum(self.check_line_ids.mapped('amount'))
            else:
                self.total_amount = 0
            for check in self.check_line_ids:
                if check.amount > 0:
                    check.write({'amount_cash': check.amount})


    @api.multi
    @api.depends('journal_id')
    @api.onchange('journal_id')
    def _compute_journal_has_checks(self):
        self.ensure_one()
        if self.journal_id:
            types = self.journal_id.inbound_payment_method_ids.mapped('code') + self.journal_id.outbound_payment_method_ids.mapped('code')
            if 'issue_check' in types:
                self.journal_has_checks = True
            else:
                self.journal_has_checks = False
                self.check_line_ids = False



    name = fields.Char(string='Name', size=64, readonly=True, default='/')
    deposit_date = fields.Date(string='Deposit Date', required=True, states={'validated': [('readonly', '=', True)]},
        default=fields.Date.context_today,translate=True)
    type = fields.Selection([('cash_in', 'Entrada de Caja'),('cash_out', 'Salida de Caja')],translate=True)
    journal_id = fields.Many2one('account.journal',string='Journal',domain=[('type', 'in', ['bank','cash'])],
        required=True,states={'validated': [('readonly', '=', True)]},translate=True)
    state = fields.Selection([('draft', 'Draft'),('validated', 'Validated'),('cancelled', 'Cancelled')],
        string='Status', default='draft', readonly=True,translate=True)
    receiptbook_id = fields.Many2one('account.payment.receiptbook','ReceiptBook',
        states={'validated': [('readonly', True)]},translate=True)
    paym_account_analytic_id = fields.Many2many('account.analytic.tag', string=' Payment Analytic Tag',translate=True,
        states={'validated': [('readonly', True)]})
    currency_id = fields.Many2one('res.currency', string='Currency', required=True,
        states={'validated': [('readonly', '=', True)]},translate=True)
    total_amount = fields.Float(string="Total Amount",digits=dp.get_precision('Account'),translate=True,
        states={'validated': [('readonly', True)]})
    move_id = fields.Many2one('account.move', string='Journal Entry', readonly=True)
    line_ids = fields.One2many('account.move.line', related='move_id.line_ids', string='Lines', readonly=True,translate=True)
    check_line_ids = fields.One2many('account.check','cashin_out_id',string='Checks',translate=True,
            states={'validated': [('readonly', True)]},ondelete="set null")
    number_of_checks = fields.Integer(compute='_compute_nrofchecks',string="Number of checks",translate=True)
    benefitiary_type = fields.Selection([('supplier', 'Supplier'), ('employee', 'Employee')],string='Benefitiary Type',
            translate=True,states={'validated': [('readonly', True)]})
    cash_account_id = fields.Many2one('account.account',string='Cash account',required=True,
            states={'validated': [('readonly', True)]})
    cash_account_analytic_id = fields.Many2many('account.analytic.tag', string='Cash Analytic Tag',translate=True,
            states={'validated': [('readonly', True)]})
    benefitiary_id = fields.Many2one('res.partner',string="Benefitiary Supplier",states={'validated': [('readonly', True)]},translate=True)
    employee_id = fields.Many2one('hr.employee',string="Benefitiary Employee",states={'validated': [('readonly', True)]},translate=True)
    journal_has_checks = fields.Boolean(compute="_compute_journal_has_checks")
    company_id = fields.Many2one('res.company','Company')
    sub_journal = fields.Many2one('setting.subtype.journal', translate=True,string="Sub Type")
    cash_reference = fields.Char(string="Referencia",translate=True)

    @api.multi
    @api.depends('benefitiary_id','employee_id')
    @api.onchange('benefitiary_type')
    def onchange_benefitiary_type(self):
        self.ensure_one()
        self.benefitiary_id = False
        self.employee_id = False

    @api.model
    def create(self, vals):
        if vals.get('journal_id'):
            journal = self.env['account.journal'].search([('id','=',vals.get('journal_id'))])
            if len(journal.outbound_payment_method_ids) > 1:
                raise UserError(_("Journal has more than 1 option in payment method"))
            if len(journal.inbound_payment_method_ids) > 1:
                raise UserError(_("Journal has more than 1 option in debit method"))
            types = journal.inbound_payment_method_ids.mapped('code') + journal.outbound_payment_method_ids.mapped('code')
            if vals.get('type') == 'cash_in' and 'issue_check' in types:
                raise UserError(_("Issue Check Journal not allowed here"))

        if vals.get('name', '/') == '/':
            type = self._context.get('default_type')
            if type == 'cash_out':
                vals['name'] = self.env['ir.sequence'].next_by_code('account.cash.out')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('account.cash.in')
        res = super(AccountCashInOut, self).create(vals)
        return res

    @api.model
    def default_get(self, fields):
        rec = super(AccountCashInOut, self).default_get(fields)
        rec['name'] = "/"
        type = self._context.get('default_type')
        company = self.env['res.company']._company_default_get('vitt_cashin_cashout')
        if type == 'cash_out':
            domain = [('document_type_id.internal_type','=','cash_out')]
        else:
            domain = [('document_type_id.internal_type','=','cash_in')]
        rec.update({'receiptbook_id': self.env['account.payment.receiptbook'].search(domain,limit=1).id})
        rec.update({'currency_id':company.currency_id.id,
                    'company_id':company.id,})
        return rec


    @api.multi
    def validate_cash(self):
        if self.journal_id.default_debit_account_id.deprecated or self.journal_id.default_debit_account_id.deprecated:
            raise UserError(_("Journal account checked as deprecated, not allowed"))
        if self.cash_account_id.deprecated:
            raise UserError(_("Cash account checked as deprecated, not allowed"))
        if self.journal_id:
            types = self.journal_id.inbound_payment_method_ids.mapped('code') + self.journal_id.outbound_payment_method_ids.mapped('code')
            if 'delivered_third_check' in types or 'received_third_check' in types:
                raise UserError(_("journal Third Checks type not allowed"))
            if 'issue_check' in types:
                if self.type == 'cash_in':
                    raise UserError(_("issue check journal type not allowed in cash-in"))
                if not self.benefitiary_type:
                    raise UserError(_("Please, Select a benefitiray type first"))
                else:
                    if self.benefitiary_type=='supplier' and not self.benefitiary_id:
                        raise UserError(_("Please, Select a Contact first"))
                    if self.benefitiary_type=='employee' and not self.employee_id:
                        raise UserError(_("Please, Select an Employee first"))
            for check in self.check_line_ids:
                if self.benefitiary_type == 'supplier':
                    if check.partner_id != self.benefitiary_id:
                        raise UserError(_("partner in check %s not the same as cash legder") % (check.number))
                if self.benefitiary_type == 'employee':
                    if check.partner_id.employee_id != self.employee_id:
                        raise UserError(_("employee in check %s not the same as cash legder") % (check.number))
        self.create_cash_nl()

    @api.multi
    def todraft_cash(self):
        for rec in self:
            for check in rec.check_line_ids:
                if check.state != 'draft':
                    raise UserError(_("check %s is not in draft state, not allowed") % (check.number))
            rec.state = 'draft'

    @api.multi
    def revert_validate(self):
        for rec in self.check_line_ids:
            if rec.state != 'handed':
                raise UserError(_('There are compromised checks, not allowed'))
        self.create_cash_nl(reverse=True)

    @api.multi
    def create_cash_nl(self,reverse=False):
        for cash in self:
            if not reverse:
                credit_account = cash.journal_id.default_debit_account_id
                debit_account = cash.cash_account_id
                cur_factor = cash.currency_id._get_conversion_rate(cash.company_id.currency_id,
                                                                   cash.currency_id)
                if cash.type == 'cash_in':
                    name = _('Entrada de Caja "%s"') % (cash.name)
                    credit_line_vals = {
                        'name': name,
                        'account_id': debit_account.id,
                        'credit': cash.total_amount / cur_factor,
                        'currency_id': cash.currency_id.id,
                        'analytic_tag_ids': [(6, False, cash.paym_account_analytic_id._ids)]
                        # 'ref': ref,
                    }
                    debit_line_vals = {
                        'name': name,
                        'account_id': credit_account.id,
                        'debit': cash.total_amount / cur_factor,
                        'currency_id': cash.currency_id.id,
                        # 'ref': ref,
                        'analytic_tag_ids': [(6, False, cash.paym_account_analytic_id._ids)]
                    }
                    if cash.currency_id.id != self.company_id.currency_id.id:
                        credit_line_vals.update({'amount_currency': cash.total_amount})
                        debit_line_vals.update({'amount_currency': -cash.total_amount})
                else:
                    name = _('Salida de Caja "%s"') % (cash.name)
                    debit_line_vals = {
                        'name': name,
                        'account_id': debit_account.id,
                        'debit': cash.total_amount / cur_factor,
                        'currency_id': cash.currency_id.id,
                        # 'ref': ref,
                        'analytic_tag_ids': [(6, False, cash.cash_account_analytic_id._ids)]
                    }
                    credit_line_vals = {
                        'name': name,
                        'account_id': credit_account.id,
                        'credit': cash.total_amount / cur_factor,
                        'currency_id': cash.currency_id.id,
                        # 'ref': ref,
                        'analytic_tag_ids': [(6, False, cash.cash_account_analytic_id._ids)]
                    }
                    if cash.currency_id.id != self.company_id.currency_id.id:
                        debit_line_vals.update({'amount_currency': cash.total_amount})
                        credit_line_vals.update({'amount_currency': -cash.total_amount})
                ref = name
                if self.cash_reference:
                    ref = self.cash_reference + '-' + name
                vals = {
                    'ref': ref,
                    'journal_id': cash.journal_id.id,
                    'date': cash.deposit_date,
                    'line_ids': [(0, False, debit_line_vals),(0, False, credit_line_vals)],
                }
                if cash.benefitiary_id:
                    vals.update({'partner_id': cash.benefitiary_id.id})
                if cash.employee_id:
                    vals.update({'partner_id': self.env['res.partner'].search([('employee_id', '=', cash.employee_id.id)],limit=1).id})
                move = self.env['account.move'].create(vals)
                move.post()
                cash.write({'move_id': move.id, 'state': 'validated'})
            if reverse:
                move = cash.move_id
                cash.write({'move_id':False, 'state':'cancelled'})
                move.write({'state':'draft'})
                move.unlink()
            for check in cash.check_line_ids:
                if reverse:
                    check.write({'state':'draft'})
                    check._add_operation('draft', cash, None, None, None)
                else :
                    check.write({'state':'handed'})
                    partner = None
                    # if self.benefitiary_type == 'supplier':
                    #     partner = cash.benefitiary_id
                    # if self.benefitiary_type == 'employee':
                    #     partner = cash.employee_id.partner_id
                    check._add_operation('handed', cash, partner, None, move.id)

    def copy(self, default=None):
        default = default or {}
        default['name'] = '/'
        res = super(AccountCashInOut, self).copy(default=default)
        return res

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.state not in ('draft','cancelled'):
                raise UserError(_("cash record %s is not in draft/canceled state, not allowed") % (rec.name))
        return super(AccountCashInOut, self).unlink()
