from datetime import datetime
from dateutil import relativedelta
from odoo import http, models, fields, api, _
from cStringIO import StringIO
import base64
from decimal import *
import time
import string

TWOPLACES = Decimal(10) ** -2

def MultiplybyRate(rate, amountincur, curcomp, invcur):
    if curcomp != invcur:
        return rate * amountincur
    else:
        return amountincur

class excel_extended(models.TransientModel):
    _name= "excel.extended"
    excel_file = fields.Binary('Download report Excel')
    file_name = fields.Char('Excel File', size=64)

class IssueChecksStates(models.Model):
    _name = "issue.checks.states"

    states = fields.Char(string="States")
    name = fields.Char(string="Name",translate=True)

class ThirdChecksStates(models.Model):
    _name = "third.checks.states"

    states = fields.Char(string="States")
    name = fields.Char(string="Name",translate=True)

class AccountCheckHistory(models.Model):
    _name = 'account.check.history'

    type = fields.Selection([
        ('issue_check', _('Issue Check')),
        ('third_check', _('Third Check')),
        ])
    date_from = fields.Date(string='Date From', required=True,
        default=datetime.now().strftime('%Y-%m-01'))
    date_to = fields.Date(string='Date To', required=True,
        default=str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])
    partner_id = fields.Many2many('res.partner',string='Partner')
    bank_id = fields.Many2one('res.bank', string='Bank')
    issue_state = fields.Many2many('issue.checks.states',string="States",translate=True)
    third_state = fields.Many2many('third.checks.states',string="States",translate=True)
    sort_order = fields.Selection([
        ('check_nr', _('Serial Nr')),
        ('partner', _('Partner')),
        ('payment_date', _('Payment Date')),
        ],translate=True,default='check_nr')
    mode = fields.Selection([
        ('detailed', _('Detailed')),
        ('overview', _('Overview')),
        ],translate=True,default='overview')
    partner_id2 = fields.Many2many('res.partner',string='Partner')

    @api.model
    def default_get(self, fields):
        res = super(AccountCheckHistory, self).default_get(fields)
        if self._context.get('default_type') == 'issue_check':
            states = self.env['issue.checks.states'].search([])
            res.update({'issue_state': [(6, 0, states._ids)]})
        if self._context.get('default_type') == 'third_check':
            states = self.env['third.checks.states'].search([])
            res.update({'third_state': [(6, 0, states._ids)]})
        return res

    @api.multi
    def ex_checkhist_report(self):
        datas = {
            'type': self.type,
            'date_froms': self.date_from,
            'date_tos': self.date_to,
            'partner_id': list(self.partner_id._ids),
            'partner_id2': list(self.partner_id2._ids),
            'bank_id': self.bank_id.id,
            'issue_state': list(self.issue_state.mapped('states')),
            'third_state': list(self.third_state.mapped('states')),
            'sort_order': self.sort_order,
            'mode': self.mode,
        }
        return self.env['report'].with_context(landscape=True).get_action(self, 'vitt_arg_check_history_reports.check_rep', data=datas)

class report_vitt_arg_check_history_reports_check_rep(models.Model):
    _name = "report.vitt_arg_check_history_reports.check_rep"

    def render_html(self,docids, data=None):
        domain = [
            ('transdate_move_id', '>=', data['date_froms']), ('transdate_move_id', '<=', data['date_tos'])
        ]
        if data['partner_id']:
            if data['type'] == 'issue_check':
                domain.append(('check_id.partner_id.id','in', data['partner_id2']))
            if data['type'] == 'third_check':
                domain.append(('check_id.partner_id.id', 'in', data['partner_id']))
        if data['bank_id']:
            domain.append(('check_id.bank_id.id', 'in', [data['bank_id']]))
        if data['type'] == 'issue_check':
            domain.append(('check_id.type','=','issue_check'))
            domain.append(('operation', 'in', data['issue_state'] or []))
        if data['type'] == 'third_check':
            domain.append(('check_id.type','!=','issue_check'))
            domain.append(('operation', 'in', data['third_state'] or []))

        checks_op = self.env['account.check.operation'].search(domain)

        sort_data = data['sort_order']
        if sort_data == 'check_nr':
            checks_op = checks_op.sorted(key=lambda r: r.check_id.number)
        if sort_data == 'partner':
            checks_op = checks_op.sorted(key=lambda r: r.check_id.partner_id.name)
        if sort_data == 'payment_date':
            checks_op = checks_op.sorted(key=lambda r: r.check_id.payment_date)

        if data['mode'] == 'overview':
            subsdata = self.env['account.check.operation']
            for op in checks_op:
                for op_f in checks_op:
                    if op.operation == op_f.operation and op.date <= op_f.date \
                            and op.check_id.number == op_f.check_id.number and op.id != op_f.id:
                        subsdata += op
            checks_op -= subsdata

        report_obj = self.env['report']
        report = report_obj._get_report_from_name('vitt_arg_check_history_reports.check_rep')
        docargs = {
            'docs': checks_op,
            'mode': data['mode'],
            'model': "account.check",
            'datat': data['third_state'],
            'datai': data['issue_state'],
            'type': data['type'],
        }
        return self.env['report'].render('vitt_arg_check_history_reports.check_rep', docargs)

class AccountCheckOperation(models.Model):
    _inherit = 'account.check.operation'

    @api.multi
    def getgrandtotals(self,data='',docs={},datat=[],datai=[],type=''):
        totval = 0
        total = 0
        for checkop in docs:
            if data=='camount_total':
                if type == 'issue_check':
                    if checkop.operation in datai or []:
                        totval = checkop.check_id.amount
                else :
                    if checkop.operation in datat or []:
                        totval = checkop.check_id.amount
            total += totval
        #total = float(MultiplybyRate(checkop.check_id.currency_rate, total, checkop.check_id.company_currency_id, checkop.check_id.currency_id))
        return Decimal(total).quantize(TWOPLACES)
