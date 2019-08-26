# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from odoo import fields, models, _, api
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)


class AccountCheckOperation(models.Model):

    _name = 'account.check.operation'
    _rec_name = 'operation'
    _order = 'date desc, id desc'
    # _order = 'create_date desc'

    # we use create_date
    date = fields.Datetime(
        # default=fields.Date.context_today,
        default=lambda self: fields.Datetime.now(),
        required=True,
    )
    check_id = fields.Many2one(
        'account.check',
        'Check',
        required=True,
        ondelete='cascade'
    )
    operation = fields.Selection([
        # from payments
        ('holding', 'Receive'),
        ('deposited', 'Deposit'),
        ('selled', 'Sell'),
        ('delivered', 'Deliver'),
        ('handed', 'Hand'),
        ('withdrawed', 'Withdrawal'),
        # from checks
        ('reclaimed', 'Claim'),
        ('rejected', 'Rejection'),
        ('debited', 'Debit'),
        ('returned', 'Return'),
        ('changed', 'Change'),
        ('cancel', 'Cancel'),
    ],
        required=True,
        translate=True,
    )
    # move_line_id = fields.Many2one(
    #     'account.move.line',
    #     ondelete='cascade',
    # )
    origin_name = fields.Char(
#        compute='_compute_origin_name'
    )
    origin = fields.Reference(
        string='Origin Document',
        translate=True,
        selection='_reference_models')
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        translate=True,
    )
    notes = fields.Text(
    )
    move_id = fields.Many2one('account.move','account move')
    owner_id = fields.Integer("Owner",ondelete="cascade")
    owner_model = fields.Char("Model",ondelete="cascade")
    transdate_move_id = fields.Date(string="Transdate",translate=True,default=lambda self: fields.Datetime.now())

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.origin:
                raise ValidationError(_(
                    'You can not delete a check operation that has an origin.'
                    '\nYou can delete the origin reference and unlink after.'))
        return super(AccountCheckOperation, self).unlink()

    # no longer needed because we try to autoclean origin
    # @api.multi
    # def clean_origin(self):
    #     self.origin = False

    @api.multi
    @api.depends('origin')
    def _compute_origin_name(self):
        """
        We add this computed method because an error on tree view displaying
        reference field when destiny record is deleted.
        As said in this post (last answer) we should use name_get instead of
        display_name
        https://www.odoo.com/es_ES/forum/ayuda-1/question/
        how-to-override-name-get-method-in-new-api-61228
        """
        for rec in self:
            try:
                if rec.origin:
                    #id, name = rec.origin.name_get()[0]
                    #origin_name = name
                    origin_name = rec.origin.display_name
                else:
                    origin_name = False
            except:
                # if we can get origin we clean it
                rec.write({'origin': False})
                origin_name = False
            rec.origin_name = origin_name

    @api.model
    def _reference_models(self):
        return [
            ('account.payment', 'Payment'),
            ('account.check', 'Check'),
            ('account.invoice', 'Invoice'),
            ('account.move', 'Journal Entry'),
            ('account.move.line', 'Journal Item'),
            ('account.check.deposit', 'Deposit'),
        ]
        # models = self.env['ir.model'].search([('state', '!=', 'manual')])
        # return [(model.model, model.name)
        #         for model in models
        #         if not model.model.startswith('ir.')]


class AccountCheck(models.Model):

    _name = 'account.check'
    _description = 'Account Check'
    _order = "id desc"
    _inherit = ['mail.thread']

    operation_ids = fields.One2many(
        'account.check.operation',
        'check_id',
    )
    name = fields.Char(
        #required=True,
        readonly=True,
        copy=False,
        states={'draft': [('readonly', False)]},
    )
    number = fields.Char(
        #required=True,
        readonly=True,
        translate=True,
        states={'draft': [('readonly', False)]},
        copy=False
    )
    checkbook_id = fields.Many2one(
        'account.checkbook',
        'Checkbook',
        readonly=True,
        translate=True,
        states={'draft': [('readonly', False)]},
        #domain=[('state','=','active')]
        # default=_get_checkbook,
    )
    type = fields.Selection(
        [('issue_check', 'Issue Check'), ('third_check', 'Third Check')],
        readonly=True,
        translate=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        #readonly=True,
        translate=True,
        readonly=True,
        states={'draft': [('readonly', False)]}
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('holding', 'Holding'),
        ('deposited', 'Deposited'),
        ('selled', 'Selled'),
        ('delivered', 'Delivered'),
        ('reclaimed', 'Reclaimed'),
        ('withdrawed', 'Withdrawed'),
        ('handed', 'Handed'),
        ('rejected', 'Rejected'),
        ('debited', 'Debited'),
        ('returned', 'Returned'),
        ('changed', 'Changed'),
        ('cancel', 'Cancel'),
    ],
        required=True,
        translate=True,
        # no need, operations are the track
        # track_visibility='onchange',
        default='draft',
        copy=False,
        compute='_compute_state',
        # search='_search_state',
        # TODO enable store, se complico, ver search o probar si un related
        # resuelve
        store=True,
    )
    issue_date = fields.Date(
        'Issue Date',
        required=True,
        readonly=True,
        translate=True,
        states={'draft': [('readonly', False)]},
        default=fields.Datetime.now,
    )
    owner_vat = fields.Char(
        'Owner Vat',
        related = 'partner_id.main_id_number',
        readonly=True,
        translate=True,
        states={'draft': [('readonly', False)]}
    )
    owner_name = fields.Many2one(
        'res.partner',
        'Owner Name',
        readonly=True,
        translate=True,
        states={'draft': [('readonly', False)]},
        domain=[('customer','=',True)]
    )
    bank_id = fields.Many2one(
        'res.bank', 'Bank',
        readonly=True,
        translate=True,
        states={'draft': [('readonly', False)]}
    )
# move.line fields
    # move_line_id = fields.Many2one(
    #     'account.move.line',
    #     'Check Entry Line',
    #     readonly=True,
    #     copy=False
    # )
    # deposit_move_line_id = fields.Many2one(
    #     'account.move.line',
    #     'Deposit Journal Item',
    #     readonly=True,
    #     copy=False
    # )

# ex campos related
    amount = fields.Monetary(
        # related='move_line_id.balance',
        currency_field='company_currency_id',
        readonly=True,
        states={'draft': [('readonly', False)]}
    )
    amount_currency = fields.Monetary(
        # related='move_line_id.amount_currency',
        currency_field='currency_id',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    currency_id = fields.Many2one(
        'res.currency',
        readonly=True,
        states={'draft': [('readonly', False)]},
        # related='move_line_id.currency_id',
    )
    payment_date = fields.Date(
        # related='move_line_id.date_maturity',
        # store=True,
        # readonly=True,
        readonly=True,
        states={'draft': [('readonly', False)]}
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        required=True,
        translate=True,
        domain=[('type', '=', 'bank')],
        readonly=True,
        states={'draft': [('readonly', False)]}
        # related='move_line_id.journal_id',
        # store=True,
        # readonly=True,
    )
    company_id = fields.Many2one(
        related='journal_id.company_id',
        readonly=True,
        store=True,
    )
    company_currency_id = fields.Many2one(
        related='company_id.currency_id',
        readonly=True,
    )

    # @api.model
    # def _get_checkbook(self):
    #     journal_id = self._context.get('default_journal_id', False)
    #     payment_subtype = self._context.get('default_type', False)
    #     if journal_id and payment_subtype == 'issue_check':
    #         checkbooks = self.env['account.checkbook'].search(
    #             [('state', '=', 'active'), ('journal_id', '=', journal_id)])
    #         return checkbooks and checkbooks[0] or False

    # @api.one
    # @api.depends('number', 'checkbook_id', 'checkbook_id.padding')
    # def _get_name(self):
    #     padding = self.checkbook_id and self.checkbook_id.padding or 8
    #     if len(str(self.number)) > padding:
    #         padding = len(str(self.number))
    #     self.name = '%%0%sd' % padding % self.number

    # @api.one
    # @api.depends(
    #     'voucher_id',
    #     'voucher_id.partner_id',
    #     'type',
    #     'third_handed_voucher_id',
    #     'third_handed_voucher_id.partner_id',
    # )
    # def _get_destiny_partner(self):
    #     partner_id = False
    #     if self.type == 'third_check' and self.third_handed_voucher_id:
    #         partner_id = self.third_handed_voucher_id.partner_id.id
    #     elif self.type == 'issue_check':
    #         partner_id = self.voucher_id.partner_id.id
    #     self.destiny_partner_id = partner_id
    
    prev_state = fields.Char(compute='_get_last_operation_name', string='Prev State', size=128)
    customer = fields.Boolean(string='Is a Customer')
    supplier = fields.Boolean(string='Is a Vendor')
    partner_id_vat = fields.Char('Partner Vat',readonly=True,translate=True,related='partner_id.main_id_number')
    notes = fields.Text()
    no_order = fields.Boolean(
        string="Cheque no a la orden",
        readonly=True,
        states={'holding': [('readonly', False)],'draft': [('readonly', False)]}
    )

    @api.multi
    @api.constrains('issue_date', 'payment_date')
    @api.onchange('issue_date', 'payment_date')
    def onchange_date(self):
        for rec in self:
            if rec.type == 'issue_check':
                if (rec.issue_date and rec.payment_date and rec.issue_date > rec.payment_date):
                    raise UserError(_('Check Payment Date must be greater than Issue Date'))
            else:
                rec.type == 'third_check'

    @api.multi
    @api.onchange('checkbook_id')
    def onchange_checkbook_id(self):
        for rec in self:
            if rec.checkbook_id:
                rec.bank_id = rec.checkbook_id.debit_journal_id.bank_id.id
                rec.payment_date = datetime.now()

    @api.multi
    @api.onchange('journal_id')
    def onchange_Journal_id(self):
        for rec in self:
            if rec.journal_id:
                issue_checks = self.env.ref('account_check.account_payment_method_issue_check')
                if (issue_checks in rec.journal_id.outbound_payment_method_ids):
                    rec.type = 'issue_check'
                    rec.supplier = True
                    rec.customer = False

                else:
                    rec.type = 'third_check'
                    rec.supplier = False
                    rec.customer = True
                rec.payment_date = datetime.now()

    @api.multi
    @api.onchange('partner_id')
    def onchange_owner_name(self):
       for rec in self:
            rec.owner_name = rec.partner_id.id

    @api.multi
    @api.constrains('name')
    @api.depends('name')
    def constrains_name(self):
        for rec in self:
            if not rec.name:
                rec.name = rec.checkbook_id.sequence_id.next_by_id()
                rec.number = rec.name
            else:
                rec.number = rec.name
            if not rec.name:
                raise UserError(_('Nro de Cheque no puede estar en blanco'))

    @api.multi
    @api.constrains('type','number','checkbook_id')
    def issue_number_interval(self):
        for rec in self:
            # if not range, then we dont check it
            if rec.type == 'issue_check' and rec.checkbook_id.range_to:

                if int(rec.number) > rec.checkbook_id.range_to:
                    raise UserError(_(
                        "Check number (%s) can't be greater than %s on "
                        "checkbook %s (%s)") % (
                        rec.number,
                        rec.checkbook_id.range_to,
                        rec.checkbook_id.name,
                        rec.checkbook_id.id,
                    ))
                elif int(rec.number) == rec.checkbook_id.range_to:
                    rec.checkbook_id.state = 'used'
        return False

    @api.model
    def create(self, vals):
        res = super(AccountCheck, self).create(vals)
        res._check_unique()
        return res


    @api.multi
    #@api.constrains('number')
    def _check_unique(self):
        for rec in self:

            lent = len(rec.name)
            lent2 = len(rec.number)
            if lent > 8 or lent2 > 8:
                raise UserError(_("error, numero de cheque mayor a 8 digitos"))
            if rec.type == 'third_check' and (lent < 8 or lent2 < 8):
                rec.name = rec.name.zfill(8)
                rec.number = rec.number.zfill(8)

            if rec.type == 'issue_check':
                same_checks = self.search([
                    ('checkbook_id', '=', rec.checkbook_id.id),
                    ('type', '=', rec.type),
                    ('name', '=', rec.name),
                ])
                if len(same_checks) > 1:
                    raise ValidationError(_(
                        'Check Number must be unique per Checkbook!\n'
                        '* Checks: %s on Checkbook %s') % (
                        rec.name, rec.checkbook_id.name))
                else:
                    if same_checks:
                        if same_checks.state != 'draft':
                            raise ValidationError(_('check already used in other payment %s') % (same_checks.number))
            elif rec.type == 'third_check':
                #same_checks -= self
                same_checks = self.search([
                    ('bank_id', '=', rec.bank_id.id),
                    ('owner_name', '=', rec.owner_name.id),
                    ('type', '=', rec.type),
                    ('number', '=', rec.number),
                ])
                if len(same_checks) > 1:
                    raise ValidationError(_(
                        'Check Number must be unique per Owner and Bank!\n'
                        '* Check ids: %s') % (
                        same_checks.ids))
                else:
                    if same_checks:
                        if same_checks.state != 'draft':
                            raise ValidationError(_('check already used in other payment %s') % (same_checks.number))
        return True

    @api.multi
    def _del_operation(self, operation):
        """
        We check that the operation that is being cancel is the last operation
        done (same as check state)
        """
        for rec in self:
            if operation and rec.state != operation:
                raise ValidationError(_(
                    'You can not cancel operation "%s" if check is in "%s" state') % (
                        rec.operation_ids._fields['operation'].convert_to_export(operation, rec.env),
                        rec._fields['state'].convert_to_export(rec.state, rec.env)))
            if rec.operation_ids:
                rec.operation_ids[0].origin = False
                #rec.operation_ids[0].unlink()

    @api.multi
    def _add_operation(self, operation, origin, partner=None, date=False, moveid=None):
        for rec in self:
            vals = {
                'operation': operation,
                'check_id': rec.id,
                'origin': '%s,%i' % (origin._name, origin.id),
                'owner_id': origin.id,
                'owner_model': origin._name,
                # 'move_line_id': move_line and move_line.id or False,
                'partner_id': partner and partner.id or False,
            }
            if date:
                vals.update({'date':date})
            if moveid:
                move = self.env['account.move'].browse(moveid)
                vals.update({'move_id':moveid,'transdate_move_id':move.date})

            rec.operation_ids.create(vals)

    @api.multi
    @api.depends('operation_ids.operation','operation_ids.date')
    def _compute_state(self):
        for rec in self:
            if rec.operation_ids:
                operation = rec.operation_ids[0].operation
                rec.state = operation
            else:
                rec.state = 'draft'

    @api.multi
    def _check_state_change(self, operation):
        """
        We only check state change from _add_operation because we want to
        leave the user the possibility of making anything from interface.
        On operation_from_state_map dictionary:
        * key is 'to state'
        * value is 'from states'
        """
        self.ensure_one()
        # if we do it from _add_operation only, not from a contraint of before
        # computing the value, we can just read it
        old_state = self.state
        # try:
        #     old_state = self.read(['state'])[0]['state']
        # except:
        #     return True
        operation_from_state_map = {
            # 'draft': [False],
            'holding': ['draft', 'deposited', 'selled', 'delivered'],
            'delivered': ['holding'],
            'deposited': ['holding', 'rejected'],
            'selled': ['holding'],
            'handed': ['draft'],
            'withdrawed': ['draft'],
            'rejected': ['delivered', 'deposited', 'selled', 'handed'],
            'debited': ['handed'],
            'returned': ['handed'],
            'changed': ['handed'],
            'cancel': ['draft'],
            'reclaimed': ['rejected'],
        }
        from_states = operation_from_state_map.get(operation)
        if not from_states:
            raise ValidationError(_(
                'Operation %s not implemented for checks!') % operation)
        if old_state not in from_states:
            raise ValidationError(_(
                'You can not "%s" a check from state "%s"!\n'
                'Check nbr (id): %s (%s)') % (
                    self.operation_ids._fields[
                        'operation'].convert_to_export(
                            operation, self.env),
                    self._fields['state'].convert_to_export(
                        old_state, self.env),
                    self.name, self.id))

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.state not in ('draft', 'cancel'):
                raise ValidationError(_('The Check must be in draft state for unlink !'))
        return super(AccountCheck, self).unlink()

# checks operations from checks

#    @api.multi
#    def bank_debit(self):
#        self.ensure_one()
#        if self.state in ['handed']:
#            vals = self.get_bank_vals(
#                'bank_debit', self.checkbook_id.debit_journal_id)
#            move = self.env['account.move'].create(vals)
#            move.post()
#            self._add_operation('debited', move)
            
    @api.multi
    def deposit_cancel(self):
        self.ensure_one()
        if self.state in ['deposited']:
            operation = self._get_operation('deposited')
            journal_id = operation.origin.journal_id
            vals = self.get_bank_vals(
                'deposited_cancel', journal_id)
            move = self.env['account.move'].create(vals)
            move.post()
            self._add_operation('holding', move, None, None, move.id)
            
    @api.multi
    def debit_cancel(self):
        self.ensure_one()
        if self.state in ['debited']:
            operation = self._get_operation('debited')
            move_reversed_id = operation.origin.reverse_moves(fields.Date.today())
            move_reversed = self.env['account.move'].search([('id','=',move_reversed_id)])
            #raise UserError(_(str(move_reversed)))
            #move_reversed.post()
            #vals = self.get_bank_vals(
            #    'deposited_cancel', journal_id)
            #move = self.env['account.move'].create(vals)
            #move.post()
            self._add_operation('handed', move_reversed, None, None, move_reversed.id)

    @api.multi
    def reject_cancel(self):
        self.ensure_one()
        if self.state in ['rejected']:
            operation = self._get_operation('rejected',False,'account.move')
            last_operation = self._get_last_operation()
            move_reversed_id = operation.origin.reverse_moves(fields.Date.today())
            move_reversed = self.env['account.move'].search([('id','=',move_reversed_id)])
            #move_reversed.post()
            #if self.type == 'third_check':
            self._add_operation(last_operation.operation, move_reversed, None, None, move_reversed.id)
            if self.type == 'issue_check':
                self.write({'state':'handed'})
            #elif self.type == 'issue_check':
            #    self._add_operation(last_operation.state, move_reversed)
                #self._add_operation('deposited', move)
            

#    @api.multi
#    def returned(self):
#        self.ensure_one()
#        if self.state in ['holding'] or self.state in ['handed']:
#            vals = self.get_bank_vals(
#                'return_check', self.journal_id)
#            move = self.env['account.move'].create(vals)
#            move.post()            
#            self._add_operation('returned', move)
            
    @api.multi
    def cancel_return(self):
        self.ensure_one()
        if self.state in ['returned']:
            if self.type == 'third_check':
                self._add_operation('holding', self)
            elif self.type == 'issue_check':
                self._add_operation('handed', self)

    @api.multi
    def _get_operation(self, operation, partner_required=False, model=''):
        self.ensure_one()
        if model:
            operation = self.operation_ids.search(
                [('check_id', '=', self.id), ('operation', '=', operation),('owner_model','=', model)], limit=1)
        else:
            operation = self.operation_ids.search(
                [('check_id', '=', self.id), ('operation', '=', operation)], limit=1)
        if partner_required:
            if not operation.partner_id:
                raise ValidationError((
                    'The %s operation has no partner linked.'
                    'You will need to do it manually.') % operation)
        return operation

    @api.multi
    def _get_last_operation(self, level=-2): # Get last Operation
        return self.operation_ids[level]


    def _get_last_operation_name(self, level=1): # Get last Operation
        for rec in self:
            try:
                rec.prev_state = rec.operation_ids[level].operation
            except:
                rec.prev_state = "No Prev State"
    @api.multi
    def reject(self):
        self.ensure_one()
        if self.state in ['deposited', 'selled']:
            operation = self._get_operation(self.state)
            if operation.origin._name == 'account.payment':
                journal = operation.origin.destination_journal_id
            # for compatibility with migration from v8
            elif operation.origin._name == 'account.move':
                journal = operation.origin.journal_id
            else:
                raise ValidationError((
                    'The deposit operation is not linked to a payment.'
                    'If you want to reject you need to do it manually.'))
            vals = self.get_bank_vals('bank_reject', journal)
            move = self.env['account.move'].create(vals)
            move.post()
            self._add_operation('rejected', move, None, None, move.id)
        elif self.state in ['delivered', 'handed']:
            operation = self._get_operation(self.state, True)
            return self.action_create_debit_note(
                'rejected', 'supplier', operation.partner_id)

    @api.multi
    def action_create_debit_note(self, operation, partner_type, partner, account, amount, account_company=None,credit=False):
        self.ensure_one()

        if partner_type == 'supplier':
            partner_account_id = partner.property_account_payable_id
            if credit:
                invoice_type = 'in_refund'
            else:
                invoice_type = 'in_invoice'
            journal_type = 'purchase'
            view_id = self.env.ref('account.invoice_supplier_form').id
        else:
            if credit:
                invoice_type = 'out_refund'
            else:
                invoice_type = 'out_invoice'
            journal_type = 'sale'
            view_id = self.env.ref('account.invoice_form').id
            partner_account_id = partner.property_account_receivable_id

        journal = self.env['account.journal'].search([
            ('company_id', '=', self.company_id.id),
            ('type', '=', journal_type),
        ], limit=1)

        product = self.env['product.product']
        print partner_type
        print operation
        print self.type
        last_operation = self._get_last_operation().operation
        print last_operation
        if self.type == 'third_check':
            if operation == 'reclaimed' and last_operation == 'deposited':
                last_operation = 'reclaimed'
            if operation == 'reclaimed' and last_operation == 'delivered':
                last_operation = 'reclaimed'

            if last_operation in ['rejected','reclaimed']:
                product = self.env['product.product'].search([('tc_state','=','tc_rejected')],limit=1)
            if last_operation == 'returned':
                product = self.env['product.product'].search([('tc_state','=','tc_canceled')],limit=1)
            account2 = product.property_account_income_id.id
        else:
            if operation == 'reclaimed' and last_operation == 'debited':
                last_operation = 'rejected'

            if last_operation in ['rejected']:
                product = self.env['product.product'].search([('oc_state','=','oc_rejected')],limit=1)
            if last_operation in ['returned','reclaimed']:
                product = self.env['product.product'].search([('oc_state','=','oc_canceled')],limit=1)
            account2 = product.property_account_expense_id.id
        if not product.id:
            raise ValidationError(_('No existe Producto asociado a este estado del cheque, por favor, cree uno nuevo'))
        if not account2:
            raise ValidationError(_('Por favor llene la cuenta de ingresos en el Item'))

        if partner_type == 'supplier':
            taxes = product.supplier_taxes_id.ids
        else:
            taxes = product.taxes_id.ids
        name = _('Check %s rejection CN') % (self.name)
        inv_line_check_vals = {
            'name': name,
            'account_id': account2,
            'invoice_line_tax_ids': [(6, 0, taxes)],
            'partner_id': partner.id,
            'price_unit': self.amount, #(self.amount_currency and self.amount_currency or self.amount),
            'product_id': product.id,
        }
        inv_line_vals = {
            # 'product_id': self.product_id.id,
            'name': 'Gastos Financieros, '+name,
            'account_id': account.id,
            'partner_id': partner.id,
            'price_unit': amount, #(self.amount_currency and self.amount_currency or self.amount),
        }
        if account == None or amount <= 0:
            lines = [(0, 0, inv_line_check_vals)]
        else:
            lines = [(0, 0, inv_line_check_vals), (0, 0, inv_line_vals)]

        if credit:
            journal_document_type_id = self.env['account.journal.document.type'].search(
                [('document_type_id.internal_type','=', 'credit_note'),
                 ('journal_id', '=', journal.id)], limit=1).id
        else:
            journal_document_type_id = self.env['account.journal.document.type'].search(
                [('document_type_id.internal_type','=', 'debit_note'),
                 ('journal_id','=', journal.id)], limit=1).id

        inv_vals = {
            'reference': name,
            'origin': _('Check nbr (id): %s (%s)') % (self.name, self.id),
            'journal_id': journal.id,
            'account_id': partner_account_id.id,
            'partner_id': partner.id,
            'journal_document_type_id': journal_document_type_id,
            'type': invoice_type,
            'invoice_line_ids': lines,
        }

        if self.currency_id:
            inv_vals.update({'currency_id':self.currency_id.id})

        if credit:
            invoice = self.env['account.invoice'].with_context(internal_type='credit_note').create(inv_vals)
        else:
            invoice = self.env['account.invoice'].with_context(internal_type='debit_note').create(inv_vals)
        self._add_operation(operation, invoice, partner, None)

        return {
            'name': name,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.invoice',
            'view_id': view_id,
            'res_id': invoice.id,
            'type': 'ir.actions.act_window',
            # 'context': {
            # #     'default_partner_id': self.partner_id.id,
            # #     'default_company_id': self.company_id.id,
            #     'default_type': invoice_type,
            #     'internal_type': 'debit_note',
            # },
            # 'domain': [('payment_id', 'in', self.payment_ids.ids)],
        }

    @api.multi
    def get_bank_vals(self, action, journal=None, date=None):
        if date == None:
            date = fields.Date.today()
        if journal == None:
            journal = self.journal_id
            
        self.ensure_one()
        # TODO improove how we get vals, get them in other functions
        if action == 'bank_debit':
            # ref = _('Debit Check Nr. ')
            # al pagar con banco se usa esta
            # self.journal_id.default_debit_account_id.id, al debitar
            # tenemos que usar esa misma
            credit_account = journal.default_debit_account_id
            # la contrapartida es la cuenta que reemplazamos en el pago
            debit_account = self.journal_id.default_credit_account_id #self.company_id._get_check_account('deferred')
            name = _('Check "%s" debited') % (self.name)
        elif action == 'bank_reject':
            # al transferir a un banco se usa esta. al volver tiene que volver
            # por la opuesta
            # self.destination_journal_id.default_credit_account_id
            credit_account = journal.default_debit_account_id
            operation = self.operation_ids.search([('check_id', '=', self.id), ('operation', '=', 'deposited')], limit=1)
            for line in operation.move_id.line_ids:
                if line.debit > 0:
                    credit_account = line.account_id

            if self.type == 'issue_check':
                debit_account = self.journal_id.default_credit_account_id
            else:
                debit_account = self.company_id._get_check_account('rejected')

            name = _('Check "%s" rejected by bank') % (self.name)
            # credit_account_id = vou_journal.default_credit_account_id.id
        elif action == 'deliver_reject':
            credit_account = self.company_id._get_check_account('third_party_bounced_endorsed')
            debit_account = self.company_id._get_check_account('rejected') #holding
            name = _('Check "%s" rejected by bank') % (self.name)
        elif action == 'supplier_rejected':
            debit_account = self.company_id._get_check_account('rejected')
            credit_account = self.company_id._get_check_account('third_party_bounced_endorsed')
            name = _('Check "%s" rejected by supplier') % (self.name)
        elif action == 'reject_cancel':
            name = _('Check "%s" bank rejection reverted') % (self.name)
            if self.type == 'third_check':
                debit_account = journal.default_debit_account_id
                credit_account = self.company_id._get_check_account('rejected')
            else:
                debit_account = self.company_id._get_check_account('own_check_cancelled')
                credit_account = journal.default_debit_account_id
        elif action == 'bank_deposited':
            credit_account = self.company_id._get_check_account('holding')
            # la contrapartida es la cuenta que reemplazamos en el pago
            debit_account = journal.default_credit_account_id
            name = _('Check "%s" deposited') % (self.name)
        elif action == 'deposited_cancel':
            credit_account = journal.default_credit_account_id
            operation = self.operation_ids.search([('check_id', '=', self.id), ('operation', '=', 'deposited')], limit=1)
            for line in operation.move_id.line_ids:
                if line.debit > 0:
                    credit_account = line.account_id

            debit_account = self.company_id._get_check_account('holding')
            name = _('Check "%s" deposit reverted') % (self.name)
        elif action == 'return_check':
            if self.type == 'issue_check':
                credit_account = self.company_id._get_check_account('own_check_cancelled')
                debit_account = journal.default_credit_account_id
            else:
                debit_account = self.company_id._get_check_account('third_party_cancelled')
                credit_account = journal.default_credit_account_id
            name = _('Check "%s" returned') % (self.name)
        elif action == 'revert_return':
            if self.type == 'issue_check':
                debit_account = self.company_id._get_check_account('own_check_cancelled')
                credit_account = journal.default_credit_account_id
            else:
                credit_account = self.company_id._get_check_account('third_party_cancelled')
                debit_account = journal.default_credit_account_id
            name = _('Check "%s" revert returned') % (self.name)
        elif action == 'changed':
            name = _('Check "%s" changed') % (self.name)
        elif action == 'supplier_reject':
            credit_account = self.company_id._get_check_account('own_check_rejected')
            debit_account = journal.default_credit_account_id
            name = _('Check "%s" rejected') % (self.name)
            # credit_account_id = vou_journal.default_credit_account_id.id 
        else:
            raise ValidationError(_(
                'Action %s not implemented for checks!') % action)

        # name = self.env['ir.sequence'].next_by_id(
        #     journal.sequence_id.id)
        # ref = self.name
        #name = _('Check "%s" rejection') % (self.name)

        debit_line_vals = {
            'name': name,
            'account_id': debit_account.id,
            # 'partner_id': partner,
            'debit': self.amount,
            'amount_currency': self.amount_currency,
            'currency_id': self.currency_id.id,
            # 'ref': ref,
        }
        credit_line_vals = {
            'name': name,
            'account_id': credit_account.id,
            # 'partner_id': partner,
            'credit': self.amount,
            'amount_currency': self.amount_currency,
            'currency_id': self.currency_id.id,
            # 'ref': ref,
        }
        return {
            'ref': name,
            'journal_id': journal.id,
            'date': date,
            'line_ids': [
                (0, False, debit_line_vals),
                (0, False, credit_line_vals)],
            # 'ref': ref,
        }
    def nextCheckNumber(self,numberwiz=''):
        if self.type == 'issue_check':
            padding = self.checkbook_id.sequence_id.padding
        else:
            padding = self.journal_id.sequence_id.padding

        if numberwiz:
            number = numberwiz
        else:
            number = str(self.checkbook_id.sequence_id.number_next_actual)
        name = '{:0{align}{width}}'.format(number, align='>', width=str(padding))
        irseq = self.checkbook_id.sequence_id
        irseq.write({'number_next_actual': self.checkbook_id.sequence_id.number_next_actual + 1})
        return name

    def copy(self, default=None):
        if self.state == 'draft':
            default = default or {}
            default['name'] = self.nextCheckNumber()
            return super(AccountCheck, self).copy(default=default)
        else:
            raise UserError(_('You cannot duplicate checks in other state than draft'))

    @api.multi
    def name_get(self):
        return [(record.id, "%s %s %s" % (record.name, record.bank_id.name, record.amount)) for record in self]

    @api.model
    def default_get(self, fields_list):
        if self._context.get('from_tree') == True:
            raise UserError(_('Not allowed, please fill it from payment'))
        result = super(AccountCheck, self).default_get(fields_list)
        return result
