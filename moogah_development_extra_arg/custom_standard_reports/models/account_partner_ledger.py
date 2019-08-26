# -*- coding: utf-8 -*-

from datetime import datetime

from odoo import models, api, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


class ReportPartnerLedger(models.AbstractModel):
    _inherit = "account.partner.ledger"

    @api.model
    def _lines(self, line_id=None):
        lines = []
        context = self.env.context
        company_id = context.get('company_id') or self.env.user.company_id
        grouped_partners = self.with_context(date_from_aml=context['date_from'], date_from=context['date_from'] and company_id.compute_fiscalyear_dates(datetime.strptime(context['date_from'], DEFAULT_SERVER_DATE_FORMAT))['date_from'] or None).group_by_partner_id(line_id)  # Aml go back to the beginning of the user chosen range but the amount on the partner line should go back to either the beginning of the fy or the beginning of times depending on the partner
        sorted_partners = sorted(grouped_partners, key=lambda p: p.name)
        unfold_all = context.get('print_mode') and not context['context_id']['unfolded_partners']
        for partner in sorted_partners:
            debit = grouped_partners[partner]['debit']
            credit = grouped_partners[partner]['credit']
            balance = grouped_partners[partner]['balance']
            lines.append({
                'id': partner.id,
                'type': 'line',
                'name': partner.name,
                'footnotes': self.env.context['context_id']._get_footnotes('line', partner.id),
                'columns': [self._format(debit), self._format(credit), self._format(balance)],
                'level': 2,
                'unfoldable': True,
                'unfolded': partner in context['context_id']['unfolded_partners'] or unfold_all,
                'colspan': 5,
            })
            unfold_partners = context['context_id'].with_context(active_test=False)['unfolded_partners']
            if partner in unfold_partners or unfold_all:
                progress = 0
                domain_lines = []
                amls = amls_all = grouped_partners[partner]['lines']
                too_many = False
                if len(amls) > 80 and not context.get('print_mode'):
                    amls = amls[-80:]
                    too_many = True
                for line in amls:
                    if self.env.context['cash_basis']:
                        line_debit = line.debit_cash_basis
                        line_credit = line.credit_cash_basis
                    else:
                        line_debit = line.debit
                        line_credit = line.credit
                    progress = progress + line_debit - line_credit
                    name = []
                    name = '-'.join(
                        line.move_id.name not in ['', '/'] and [line.move_id.name] or [] +
                        line.ref not in ['', '/'] and [line.ref] or [] +
                        line.name not in ['', '/'] and [line.name] or []
                    )
                    if len(name) > 35 and not self.env.context.get('no_format'):
                        name = name[:32] + "..."
                    number = line.full_reconcile_id.name
                    if line.invoice_id:
                        number = line.invoice_id.display_name
                    if line.payment_id:
                        number = line.payment_id.display_name
                    domain_lines.append({
                        'id': line.id,
                        'type': 'move_line_id',
                        'move_id': line.move_id.id,
                        'action': line.get_model_id_and_name(),
                        'name': line.date,
                        'footnotes': self.env.context['context_id']._get_footnotes('move_line_id', line.id),
                        'columns': [line.journal_id.code, line.account_id.code, name, number,
                                    line_debit != 0 and self._format(line_debit) or '',
                                    line_credit != 0 and self._format(line_credit) or '',
                                    self._format(progress)],
                        'level': 1,
                    })
                initial_debit = grouped_partners[partner]['initial_bal']['debit']
                initial_credit = grouped_partners[partner]['initial_bal']['credit']
                initial_balance = grouped_partners[partner]['initial_bal']['balance']
                domain_lines[:0] = [{
                    'id': partner.id,
                    'type': 'initial_balance',
                    'name': _('Initial Balance'),
                    'footnotes': self.env.context['context_id']._get_footnotes('initial_balance', partner.id),
                    'columns': ['', '', '', '', self._format(initial_debit), self._format(initial_credit), self._format(initial_balance)],
                    'level': 1,
                }]
                domain_lines.append({
                    'id': partner.id,
                    'type': 'o_account_reports_domain_total',
                    'name': _('Total') + ' ' + (partner.name or ''),
                    'footnotes': self.env.context['context_id']._get_footnotes('o_account_reports_domain_total', partner.id),
                    'columns': ['', '', '', '', self._format(debit), self._format(credit), self._format(balance)],
                    'level': 1,
                })
                if too_many:
                    domain_lines.append({
                        'id': partner.id,
                        'domain': "[('id', 'in', %s)]" % amls_all.ids,
                        'type': 'too_many_partners',
                        'name': _('There are more than 80 items in this list, click here to see all of them'),
                        'footnotes': {},
                        'colspan': 8,
                        'columns': [],
                        'level': 3,
                    })
                lines += domain_lines
        return lines


class ReportPartnerLedgerContext(models.TransientModel):
    _inherit = "account.partner.ledger.context"

    def get_columns_names(self):
        return [_('JRNL'), _('Account'), _('Ref'), _('Official Number'), _('Debit'), _('Credit'), _('Balance')]
