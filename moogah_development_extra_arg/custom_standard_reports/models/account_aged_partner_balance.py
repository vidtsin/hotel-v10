# -*- coding: utf-8 -*-

from odoo import models, api, _


class ReportAccountAgedPartner(models.AbstractModel):
    _inherit = "account.aged.partner"

    @api.model
    def _lines(self, context, line_id=None):
        sign = -1.0 if self.env.context.get('aged_balance') else 1.0
        lines = []
        results, total, amls = self.env['report.account.report_agedpartnerbalance']._get_partner_move_lines([self._context['account_type']], self._context['date_to'], 'posted', 30)
        for values in results:
            if line_id and values['partner_id'] != line_id:
                continue
            vals = {
                'id': values['partner_id'] and values['partner_id'] or -1,
                'name': values['name'],
                'level': 0 if values['partner_id'] else 2,
                'type': values['partner_id'] and 'partner_id' or 'line',
                'footnotes': context._get_footnotes('partner_id', values['partner_id']),
                'columns': [values['direction'], values['4'], values['3'], values['2'], values['1'], values['0'], values['total']],
                'trust': values['trust'],
                'unfoldable': values['partner_id'] and True or False,
                'unfolded': values['partner_id'] and (values['partner_id'] in context.unfolded_partners.ids) or False,
            }
            vals['columns'] = [self._format(sign * t) for t in vals['columns']]
            vals['columns'].insert(0, '')
            lines.append(vals)
            if values['partner_id'] in context.unfolded_partners.ids:
                for line in amls[values['partner_id']]:
                    aml = line['line']
                    display_name = ''
                    if aml.invoice_id:
                        display_name = aml.invoice_id.display_name
                    if aml.payment_id:
                        display_name = aml.payment_id.display_name
                    vals = {
                        'id': aml.id,
                        'name': aml.move_id.name if aml.move_id.name else '/',
                        'move_id': aml.move_id.id,
                        'action': aml.get_model_id_and_name(),
                        'level': 1,
                        'type': 'move_line_id',
                        'footnotes': context._get_footnotes('move_line_id', aml.id),
                        'columns': [line['period'] == 6-i and self._format(sign * line['amount']) or '' for i in range(7)],
                    }
                    vals['columns'].insert(0, display_name)
                    lines.append(vals)
                vals = {
                    'id': values['partner_id'],
                    'type': 'o_account_reports_domain_total',
                    'name': _('Total '),
                    'footnotes': self.env.context['context_id']._get_footnotes('o_account_reports_domain_total', values['partner_id']),
                    'columns': [values['direction'], values['4'], values['3'], values['2'], values['1'], values['0'], values['total']],
                    'level': 1,
                }
                vals['columns'] = [self._format(sign * t) for t in vals['columns']]
                vals['columns'].insert(0, '')
                lines.append(vals)
        if total and not line_id:
            total_line = {
                'id': 0,
                'name': _('Total'),
                'level': 0,
                'type': 'o_account_reports_domain_total',
                'footnotes': context._get_footnotes('o_account_reports_domain_total', 0),
                'columns': [total[6], total[4], total[3], total[2], total[1], total[0], total[5]],
            }
            total_line['columns'] = [self._format(sign * t) for t in total_line['columns']]
            total_line['columns'].insert(0, '')
            lines.append(total_line)
        return lines


class AccountContextAgedReceivable(models.TransientModel):
    _inherit = "account.context.aged.receivable"

    def get_columns_names(self):
        return [_('Official Number'), _("Not&nbsp;due&nbsp;on&nbsp;&nbsp; %s") % self.date_to, _("0&nbsp;-&nbsp;30"), _("30&nbsp;-&nbsp;60"), _("60&nbsp;-&nbsp;90"), _("90&nbsp;-&nbsp;120"), _("Older"), _("Total")]

    @api.multi
    def get_columns_types(self):
        return ["text", "number", "number", "number", "number", "number", "number", "number"]


class AccountContextAgedPayable(models.TransientModel):
    _inherit = "account.context.aged.payable"

    def get_report_obj(self):
        return self.env['account.aged.payable']

    def get_columns_names(self):
        return [_('Official Number'), _("Not&nbsp;due&nbsp;on&nbsp;&nbsp; %s") % self.date_to, _("0&nbsp;-&nbsp;30"), _("30&nbsp;-&nbsp;60"), _("60&nbsp;-&nbsp;90"), _("90&nbsp;-&nbsp;120"), _("Older"), _("Total")]

    @api.multi
    def get_columns_types(self):
        return ["text", "number", "number", "number", "number", "number", "number", "number"]
