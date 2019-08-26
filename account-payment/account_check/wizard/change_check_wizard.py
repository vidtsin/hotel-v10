# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError,UserError



class account_change_check_wizard(models.TransientModel):
    _name = 'account.change.check.wizard'

    @api.model
    def get_original_check(self):
        return self.original_check_id.browse(self._context.get('active_id'))

    original_check_id = fields.Many2one(
        'account.check',
        'Original Check',
        required=True,
        default=get_original_check,
        ondelete='cascade',
    )
    journal_id = fields.Many2one(
        related='original_check_id.journal_id',
    )
    type = fields.Selection(
        related='original_check_id.type',
    )
    number = fields.Integer(
        'Number',
        required=True,
        #readonly=True,
        #related='checkbook_id.sequence_id.number_next_actual',
    )
    issue_date = fields.Date(
        'Issue Date',
        required=True,
        default=fields.Date.context_today,
    )
    payment_date = fields.Date(
        'Payment Date',
        help="Only if this check is post dated",
    )

    # issue checks
    checkbook_id = fields.Many2one(
        'account.checkbook',
        'Checkbook',
        ondelete='cascade',
    )
    issue_check_subtype = fields.Selection(
        related='checkbook_id.issue_check_subtype',
    )

    # third checks
    bank_id = fields.Many2one(
        'res.bank', 'Bank',
    )
    owner_vat = fields.Char(
        'Owner Vat',
    )
    owner_name = fields.Many2one(
        'res.partner',
        'Owner Name',
        readonly=True,
        translate=True,
    )

    @api.onchange('checkbook_id')
    def compute_number(self):
        if self.original_check_id.type == 'issue_check':
            self.number = self.checkbook_id.sequence_id.number_next_actual
        else:
            pass
    
    @api.one
    @api.constrains('number','checkbook_id', 'original_check_id')
    def _contraint_number(self):
        if self.number > 0:
            pass
        else:
            raise ValidationError(
                    _('Check Number Can\'t be Zero !'))                
                

        
    @api.onchange('original_check_id')
    def change_original_check(self):
        self.checkbook_id = self.original_check_id.checkbook_id
        self.owner_vat = self.original_check_id.owner_vat
        self.owner_name = self.original_check_id.owner_name.id
        #self.bank_id = self.journal_id.bank_id

    @api.multi
    def change(self):
        self.ensure_one()
        number = self.original_check_id.nextCheckNumber(self.number)
        if number != "0":
            vals = {
                'name': number,                                 #-------------------------- wizard
                'number': number,                               #-------------------------- wizard
                'checkbook_id': self.checkbook_id.id,           #-------------------------- wizard
                'type': self.original_check_id.type,
                'partner_id': self.original_check_id.partner_id.id,
                #'state': self.original_check_id.state,
                'state': 'draft',
                'issue_date': self.issue_date,                  #--------------------------- wizard
                'owner_vat': self.original_check_id.owner_vat,
                'owner_name': self.original_check_id.owner_name.id,
                'bank_id': self.bank_id.id,                     #--------------------------- wizard
                'amount': self.original_check_id.amount,
                'amount_currency': self.original_check_id.amount_currency,
                'currency_id': self.original_check_id.currency_id.id,
                'payment_date': self.payment_date,              #---------------------------- wizard
                'journal_id': self.original_check_id.journal_id.id,
                'company_id': self.original_check_id.company_id.id,
                'company_currency_id': self.original_check_id.company_currency_id.id
            }
            if self.original_check_id.type == 'issue_check':
                vals.update({'bank_id':self.checkbook_id.debit_journal_id.bank_id.id})
            new_check_mod = self.env['account.check']
            new_check = new_check_mod.create(vals)

            if self.original_check_id.type == 'issue_check':
                paym = self.env['account.payment'].search([('check_name','=',self.original_check_id.id)])
                if paym:
                    paym.write({'check_name': new_check.id, 'check_ids': new_check.id, 'check_id': new_check.id})
            else:
                paym = self.env['account.payment'].search([('check_ids', '=', self.original_check_id.id)])
                if paym:
                    paym.write({'check_ids': new_check.id, 'check_id': new_check.id})
            new_check.write({'state':self.original_check_id.state})

            #new_check = self.original_check_id.sudo().copy(vals)
            self.original_check_id.sudo().write({
                #'replacing_check_id': new_check.id,
                'amount': 0.0,
                'company_currency_amount': 0.0,
            })
        
            self.original_check_id._add_operation('changed', new_check)
            if self.original_check_id.type == 'issue_check':
                new_check._add_operation('handed', self.original_check_id)
            else:
                new_check._add_operation('holding', self.original_check_id)


            return new_check
        else:
            raise UserError(_("Error in Number"))