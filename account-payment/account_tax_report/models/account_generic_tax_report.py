# -*- coding: utf-8 -*-
from openerp import models, api, fields, _
import logging
_logger = logging.getLogger(__name__)


class report_account_generic_tax_report(models.AbstractModel):
    _inherit = "account.generic.tax.report"

    # overwrite _lines method. the var 'type' needs customer and supplier (added in this module)

    @api.model
    def _lines(self):
        taxes = {}
        context = self.env.context
        for tax in self.env['account.tax'].search([]):
            taxes[tax.id] = {'obj': tax, 'show': False, 'periods': [{'net': 0, 'tax': 0}]}
            for period in context['periods']:
                taxes[tax.id]['periods'].append({'net': 0, 'tax': 0})
        period_number = 0
        self._compute_from_amls(taxes, period_number)
        for period in context['periods']:
            period_number += 1
            self.with_context(date_from=period[0], date_to=period[1])._compute_from_amls(taxes, period_number)
        lines = []
        types = ['sale', 'purchase', 'supplier', 'customer']
        groups = dict((tp, {}) for tp in types)
        for key, tax in taxes.items():
            if tax['obj'].type_tax_use == 'none':
                continue
            if tax['obj'].children_tax_ids:
                tax['children'] = []
                for child in tax['obj'].children_tax_ids:
                    if child.type_tax_use != 'none':
                        continue
                    tax['children'].append(taxes[child.id])
            if tax['obj'].children_tax_ids and not tax.get('children'):
                continue
            groups[tax['obj'].type_tax_use][key] = tax
        line_id = 0
        for tp in types:
            sign = tp == 'sale' and -1 or 1
            lines.append({
                'id': line_id,
                'name': tp == 'sale' and _('Sale') or _('Purchase'),
                'type': 'line',
                'footnotes': self.env.context['context_id']._get_footnotes('line', tp),
                'unfoldable': False,
                'columns': ['' for k in range(0, (len(context['periods']) + 1) * 2)],
                'level': 1,
            })
            for key, tax in sorted(groups[tp].items(), key=lambda k: k[1]['obj'].sequence):
                if tax['show']:
                    lines.append({
                        'id': tax['obj'].id,
                        'name': tax['obj'].name + ' (' + str(tax['obj'].amount) + ')',
                        'type': 'tax_id',
                        'footnotes': self.env.context['context_id']._get_footnotes('tax_id', tax['obj'].id),
                        'unfoldable': False,
                        'columns': sum([[self._format(period['net'] * sign), self._format(period['tax'] * sign)] for period in tax['periods']], []),
                        'level': 1,
                    })
                    for child in tax.get('children', []):
                        lines.append({
                            'id': child['obj'].id,
                            'name': '   ' + child['obj'].name + ' (' + str(child['obj'].amount) + ')',
                            'type': 'tax_id',
                            'footnotes': self.env.context['context_id']._get_footnotes('tax_id', child['obj'].id),
                            'unfoldable': False,
                            'columns': sum([[self._format(period['net'] * sign), self._format(period['tax'] * sign)] for period in child['periods']], []),
                            'level': 2,
                        })
            line_id += 1
        return lines
