# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from odoo import fields, models, _, api
from odoo.exceptions import UserError
import re
import logging
# import openerp.addons.decimal_precision as dp
_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):

    _inherit = 'account.payment'
    # _name = 'account.check'
    # _description = 'Account Check'
    # _order = "id desc"
    # _inherit = ['mail.thread']

    # communication = fields.Char(
    #     # because onchange function is not called on onchange and we want
    #     # to clean check number name
    #     copy=False,
    # )
    # TODO tal vez renombrar a check_ids
    check_ids = fields.Many2one(
        'account.check',
        # 'account.move.line',
        # 'check_deposit_id',
        string='Checks',
        copy=False,
        translate=True,
        readonly=True,
        states={'draft': [('readonly', '=', False)]},
        ondelete = 'set null',
    )
    #{ not used anymore
    # only for v8 comatibility where more than one check could be received
    # or issued
    check_ids_copy = fields.Many2one(
        related='check_ids',
        readonly=True,
        ondelete='set null',
    )
    #} not used anymore
    readonly_currency_id = fields.Many2one(
        related='currency_id',
        readonly=True,
    )
    readonly_amount = fields.Monetary(
        # string='Payment Amount',
        # required=True
        related='amount',
        readonly=True,
    )
    # we add this field for better usability on issue checks and received
    # checks. We keep m2m field for backward compatibility where we allow to
    # use more than one check per payment
    check_id = fields.Many2one(
        'account.check',
        #compute='_compute_check',
        string='Check',
        translate=True,
        # string='Payment Amount',
        # required=True
        ondelete='set null',
    )

    @api.multi
    @api.depends('check_ids')
    def _compute_check(self):
        for rec in self:
            # we only show checks for issue checks or received thid checks
            # if len of checks is 1
            if rec.payment_method_code in (
                    'received_third_check',
                    'issue_check',) and len(rec.check_ids) == 1:
                rec.check_id = rec.check_ids[0].id

# check fields, just to make it easy to load checks without need to create
# them by a m2o record
    check_name = fields.Many2one(
        'account.check',
        'Check Name',
        # required=True,
        readonly=True,
        copy=False,
        translate=True,
        states={'draft': [('readonly', False)]},
        ondelete='set null',
    )
    check_number = fields.Integer(
        'Check Number',
        # required=True,
        readonly=True,
        translate=True,
        states={'draft': [('readonly', False)]},
        copy=False
    )
    check_issue_date = fields.Date(
        'Check Issue Date',
        # required=True,
        #readonly=True,
        translate=True,
        copy=False,
        #states={'draft': [('readonly', False)]},
        default=fields.Date.context_today,
    )
    check_payment_date = fields.Date(
        'Check Payment Date',
        readonly=True,
        translate=True,
        help="Only if this check is post dated",
        states={'draft': [('readonly', False)]}
    )
    checkbook_id = fields.Many2one(
        'account.checkbook',
        'Checkbook',
        readonly=True,
        translate=True,
        states={'draft': [('readonly', False)]},
        # TODO hacer con un onchange
        # default=_get_checkbook,
    )
    check_subtype = fields.Selection(
        related='checkbook_id.issue_check_subtype',
    )
    check_bank_id = fields.Many2one(
        'res.bank',
        'Check Bank',
        readonly=True,
        translate=True,
        copy=False,
        states={'draft': [('readonly', False)]}
    )
    check_owner_vat = fields.Char(
        # TODO rename to Owner VAT
        'Check Owner Vat',
        translate=True,
        readonly=True,
        copy=False,
        states={'draft': [('readonly', False)]}
    )
    check_owner_name = fields.Char(
        'Check Owner Name',
        readonly=True,
        translate=True,
        copy=False,
        states={'draft': [('readonly', False)]}
    )
    check_type = fields.Char(
        compute='_compute_check_type',
        # this fields is to help with code and view
    )
    #readonly_amount2 = fields.Monetary(string='Monto a Pagar',readonly=True)
    no_order = fields.Boolean(string="Cheque no a la orden")

    @api.multi
    @api.depends('payment_method_code')
    def _compute_check_type(self):
        for rec in self:
            if rec.payment_method_code == 'issue_check':
                rec.check_type = 'issue_check'
            elif rec.payment_method_code in ['received_third_check','delivered_third_check']:
                rec.check_type = 'third_check'


# on change methods

    # @api.constrains('check_ids')
    @api.onchange('check_ids', 'payment_method_code')
    def onchange_checks(self):
        # we only overwrite if payment method is delivered
        if self.payment_method_code == 'delivered_third_check':
            self.amount = sum(self.check_ids.mapped('amount'))

    @api.onchange('amount')
    def ojg_onchange_amount(self):
        if self.check_name:
            if self.check_name.amount > 0:
                self.amount = self.check_name.amount


    @api.depends('checkbook_id','check_name')
    @api.onchange('check_name')
    @api.constrains('check_name')
    def onchange_check_name(self):
        if self.check_name:
            if not ((self.partner_id == self.check_name.partner_id or self.check_name.partner_id.id==False) \
                    and self.check_name.state == 'draft' and self.checkbook_id == self.check_name.checkbook_id):

                raise UserError(_('the check should be with the correct partner/checkbook/state'))
            if not (self.check_name.amount > 0):
                raise UserError(_('the amount in check should be greater than 0'))

            if not self.check_name.partner_id.id:
                raise UserError(_('the partner in check shouldn\'t be empty'))

            self.amount = self.check_name.amount
            self.check_number = self.check_name.number
            self.check_issue_date = self.check_name.issue_date
            self.check_payment_date = self.check_name.payment_date
            if self.payment_method_code != 'issue_check':
                self.check_bank_id = self.check_name.bank_id

    @api.onchange('check_issue_date', 'check_payment_date')
    def onchange_date(self):
        if (
                self.check_issue_date and self.check_payment_date and
                self.check_issue_date > self.check_payment_date):
            self.check_payment_date = False
            raise UserError(_('Check Payment Date must be greater than Issue Date'))

    #@api.one
    @api.onchange('partner_id')
    def onchange_partner_check(self):
        self.ensure_one()
        commercial_partner = self.partner_id.commercial_partner_id
        # self.check_bank_id = (
        #     commercial_partner.bank_ids and
        #     commercial_partner.bank_ids[0].bank_id.id or False)
        self.check_owner_name = commercial_partner.name
        # TODO use document number instead of vat?
        self.check_owner_vat = commercial_partner.main_id_number

    @api.onchange('payment_method_code')
    def _onchange_payment_method_code(self):
        if self.payment_method_code == 'issue_check':
            checkbook = self.env['account.checkbook'].search([
                 ('state', '=', 'active'),
                 ('journal_id', '=', self.journal_id.id)],
                 limit=1)
            self.checkbook_id = checkbook
            
    #@api.onchange('journal_id')
    @api.onchange('checkbook_id')
    def onchange_checkbook(self):
        if self.checkbook_id:
            #self.check_number = self.checkbook_id.sequence_id.number_next
            self.check_name = None
            self.amount = 0.0
            
    def valid_field_third_checks(self, vals):
        third_checks = self.env.ref(
            'account_check.account_payment_method_received_third_check')

        msg=[]
                
        if vals['payment_method_id'] == third_checks.id:
            if vals['check_number'] <= 0:
                msg.append("Check Number")
            '''if vals['amount'] <= 0:
                msg.append("Amount")
             if vals['check_issue_date']:
                msg.append("Issue Date")
            if vals['payment_date']:
                msg.append("Payment Date")
            if vals['check_bank_id']:
                msg.append("Bank")
            if vals['check_owner_vat']:
                msg.append("Owner VAT")   
            if vals['check_owner_name']:
                msg.append("Owner Name") '''
                
                
            if len(msg) > 0:
                raise UserError(_('Por favor completar. '+str(msg)))

# CRUD methods
# Create
    @api.model
    def create(self, vals):
        #self.valid_field_third_checks(vals)
        res = super(AccountPayment, self.sudo()).create(vals)
        res.hide_payment_method = True
        if res.check_name or res.check_number:
            if res.check_name:
                if not ((res.partner_id == res.check_name.partner_id or res.check_name.partner_id.id==False)
                    and res.check_name.state == 'draft' and res.checkbook_id == res.check_name.checkbook_id):

                    raise UserError(_('the check should be with the correct partner/checkbook/state'))
        res.onchange_partner_check()
        return res;

    @api.multi
    def write(self, vals):
        vals.update({'hide_payment_method':True})
        res = super(AccountPayment, self.sudo()).write(vals)
        return res;

    @api.multi
    def cancel(self):
        res = super(AccountPayment, self).cancel()
        for rec in self:
            rec.do_checks_operations(cancel=True)
            # if rec.check_id:
            #     # rec.check_id._add_operation('cancel')
            #     rec.check_id._del_operation()
            #     rec.check_id.unlink()
            # elif rec.check_ids:
            #     rec.check_ids._del_operation()
        return res

    def create_check(self, check_type, operation, bank, origin=None, move_id=None):
        check_vals = {
            'owner_name': int(self.partner_id.id), #check_owner_name,
            'owner_vat': self.check_owner_vat,
            'partner_id': int(self.partner_id.id),
            'number': self.check_name.name,
            'name': self.check_name.name,
            'checkbook_id': int(self.checkbook_id.id),
            'type': self.check_type,
            'journal_id': int(self.journal_id.id),
            'amount': float(self.amount),
            'payment_date': self.check_payment_date,
            # TODO arreglar que monto va de amount y cual de amount currency
            # 'amount_currency': self.amount,
            'currency_id': int(self.currency_id.id),
            'notes': self.communication,
            'no_order': self.no_order,
        }
        if check_type == 'third_check':
            check_vals.update({'bank_id':int(bank.id)})

        if not self.check_name:
            check_vals.update({'issue_date':self.check_issue_date})
            if check_type == 'third_check':
                check_vals.update({'name': self.check_number})
                check_vals.update({'number': self.check_number})
            check = self.env['account.check'].create(check_vals)

        else:
            check = self.check_name
            written = check.write(check_vals)
        #self.check_ids = [(4, check.id, False)]
        self.check_ids = check.id

        if move_id:
            move = self.env['account.move'].search([('id','=',move_id)])
            for line in move.line_ids:
                line.write({'check_id':check.id})
        if operation:
            check._add_operation(operation, origin, self.partner_id, None, move_id)
        return check

    @api.multi
    def get_third_check_account(self):
        """
        For third checks, if we use a journal only for third checks, we use
        accounts on journal, if not we use company account
        """
        self.ensure_one()
        if self.payment_type in ('outbound', 'transfer'):
            account = self.journal_id.default_debit_account_id
            methods_field = 'outbound_payment_method_ids'
        else:
            account = self.journal_id.default_credit_account_id
            methods_field = 'inbound_payment_method_ids'
        if len(self.journal_id[methods_field]) > 1 or not account:
            account = self.company_id._get_check_account('holding')
        return account

    @api.multi
    def do_checks_operations(self, vals={}, cancel=False):
        """
        Check attached .ods file on this module to understand checks workflows
        This method is called from:
        * cancellation of payment to execute delete the right operation and
            unlink check if needed
        * from _get_liquidity_move_line_vals to add check operation and, if
            needded, change payment vals and/or create check and
        """
        self.ensure_one()
        rec = self
        if not rec.check_type:
            # continue
            return vals
        if (
                rec.payment_method_code == 'received_third_check' and
                rec.payment_type == 'inbound' and
                rec.partner_type == 'customer'):
            operation = 'holding'
            if cancel:
                _logger.info('Cancel Receive Check')
                rec.check_ids._del_operation(operation)
                rec.check_ids = False
                return None

            _logger.info('Receive Check')
            self.create_check('third_check', operation, self.check_bank_id, self.payment_group_id,self.move_line_ids[0].move_id.id)
            vals['date_maturity'] = self.check_payment_date
            vals['account_id'] = self.get_third_check_account().id
        elif (
                rec.payment_method_code == 'delivered_third_check' and
                rec.payment_type == 'transfer' and
                rec.destination_journal_id.type == 'cash'):
            operation = 'selled'
            if cancel:
                _logger.info('Cancel Sell Check')
                rec.check_ids._del_operation(operation)
                return None

            _logger.info('Sell Check')
            rec.check_ids._add_operation(operation, rec.payment_group_id, False, False, self.move_line_ids[0].move_id.id)
            vals['account_id'] = self.get_third_check_account().id
        elif (
                rec.payment_method_code == 'delivered_third_check' and
                rec.payment_type == 'transfer' and
                rec.destination_journal_id.type == 'bank'):
            operation = 'deposited'
            if cancel:
                _logger.info('Cancel Deposit Check')
                rec.check_ids._del_operation(operation)
                return None

            _logger.info('Deposit Check')
            rec.check_ids._add_operation(operation, rec.payment_group_id, False, False, self.move_line_ids[0].move_id.id)
            vals['account_id'] = self.get_third_check_account().id
        elif (
                rec.payment_method_code == 'delivered_third_check' and
                rec.payment_type == 'outbound' and
                rec.partner_type == 'supplier'):
            operation = 'delivered'
            if cancel:
                _logger.info('Cancel Deliver Check')
                rec.check_ids._del_operation(operation)
                return None

            _logger.info('Deliver Check')
            rec.check_ids._add_operation(operation, rec.payment_group_id, rec.partner_id, False, self.move_line_ids[0].move_id.id)
            vals['account_id'] = self.get_third_check_account().id
        elif (
                rec.payment_method_code == 'issue_check' and
                rec.payment_type == 'outbound' and
                rec.partner_type == 'supplier'):
            operation = 'handed'
            if cancel:
                _logger.info('Cancel Hand Check')
                rec.check_ids._del_operation(operation)
                rec.check_ids = False
                return None

            _logger.info('Hand Check')
            self.create_check('issue_check', operation, self.check_bank_id, self.payment_group_id,self.move_line_ids[0].move_id.id)
            ## vals['date_maturity'] = self.check_payment_date
            # if check is deferred, change account
            if self.check_subtype == 'deferred':
                vals['account_id'] = self.company_id._get_check_account('deferred').id
        elif (
                rec.payment_method_code == 'issue_check' and
                rec.payment_type == 'transfer' and
                rec.destination_journal_id.type == 'cash'):
            operation = 'withdrawed'
            if cancel:
                _logger.info('Cancel Withdrawal Check')
                rec.check_ids._del_operation(operation)
                rec.check_ids = False
                return None

            _logger.info('Hand Check')
            self.create_check('issue_check', operation, self.check_bank_id, self.payment_group_id,self.move_line_ids[0].move_id.id)
            vals['date_maturity'] = self.check_payment_date
            # if check is deferred, change account
            # si retiramos por caja directamente lo sacamos de banco
            # if self.check_subtype == 'deferred':
            #     vals['account_id'] = self.company_id._get_check_account(
            #         'deferred').id
        else:
            raise UserError(_(
                'This operatios is not implemented for checks:\n'
                '* Payment type: %s\n'
                '* Partner type: %s\n'
                '* Payment method: %s\n'
                '* Destination journal: %s\n' % (
                    rec.payment_type,
                    rec.partner_type,
                    rec.payment_method_code,
                    rec.destination_journal_id.type)))
        return vals

    @api.multi
    def validate_checks(self):
        for paym in self:
            if paym.payment_group_id.id:
                checks = []
                for rec in paym.payment_group_id.payment_ids:
                    if rec.payment_type == 'outbound':
                        if rec.check_ids.id:
                            if (str(rec.check_ids.id) + str(rec.check_ids.bank_id.id)
                                + str(rec.check_ids.checkbook_id.id)) in checks:

                                raise UserError(_('Same check should be used once %s')%(rec.check_ids.name))
                            else:
                                checks.append(str(rec.check_ids.id) + str(rec.check_ids.bank_id.id)
                                              + str(rec.check_ids.checkbook_id.id))

                        else:
                            if rec.check_name.id:
                                if (str(rec.check_name.id) + str(rec.check_name.bank_id.id)
                                    + str(rec.check_name.checkbook_id.id)) in checks:

                                    raise UserError(_('Same check should be used once %s')%(rec.check_name.name))
                                else:
                                    checks.append(str(rec.check_name.id) + str(rec.check_name.bank_id.id)
                                                  + str(rec.check_name.checkbook_id.id))


                    if rec.payment_type == 'inbound':
                        if rec.check_number:
                            if (str(rec.check_number) + str(rec.check_bank_id.id)) in checks:

                                raise UserError(_('Same check should be used once %s')%(rec.check_number))
                            else:
                                checks.append(str(rec.check_number) + str(rec.check_bank_id.id))


                break

    @api.multi
    def post(self):
        super(AccountPayment, self).post()
        #self.create_check(self.check_type, None, self.check_bank_id, None)
        self.validate_checks()
        for rec in self:
            rec.do_checks_operations()

    # @api.model
    # def default_get(self, fields):
    #     res = super(AccountPayment, self).default_get(fields)
    #     if 'amount' in res:
    #         #context = dict(self._context or {})
    #         #res['partner_id'] = self.env['res.partner'].browse(context['default_partner_id']).id
    #         res['readonly_amount2'] = res['amount']
    #     return res

    @api.multi
    def unlink(self):
        for paym in self:
            if paym.check_id.id and paym.check_id.state != 'draft':
                if paym.check_id.type == 'issue_check':
                    if paym.check_id.state != 'handed':
                        raise UserError(_('No es posible Cancelar. Existe uno o más Cheques Propios que no se'
                                        ' encuentran en un estado válido (Emitido)'))
                else:
                    raise UserError(_('No es posible Cancelar. Existe uno o más Cheques 3ros que no se'
                                      ' encuentran en un estado válido'))
        return super(AccountPayment, self).unlink()


    # todo el codigo que se borro de aca esta en el commint 474f2f165cec3741afd14de412caaecd372acc30 de bitbucket