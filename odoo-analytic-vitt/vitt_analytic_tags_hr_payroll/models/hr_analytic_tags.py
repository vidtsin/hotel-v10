# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import models, api, fields, _
from odoo.exceptions import ValidationError


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    @api.multi
    def compute_sheet(self):
        res = super(HrPayslip, self).compute_sheet()

        if res:
            analytic_tag_obj = self.env['account.analytic.tag']
            for payslip in self:
                contract_dom = [('employee_id', '=', payslip.employee_id.id), ('state', 'in', ['open'])]
                employee_contracts = self.env['hr.contract'].search(contract_dom)
                contract_tags_ids = []
                for contract in employee_contracts:
                    contract_tags_ids += contract.analytic_tag_ids.ids

                contract_tags_ids = list(set(contract_tags_ids))
                contract_tags = analytic_tag_obj.browse(contract_tags_ids)
                for payslip_line in payslip.line_ids:
                    new_tags = payslip_line.salary_rule_id.analytic_tag_ids + contract_tags
                    payslip_line.analytic_tag_ids = analytic_tag_obj._set_tags(tags=payslip_line.analytic_tag_ids, new_tags=new_tags)

        return res

    @api.multi
    def action_payslip_done(self):
        res = super(HrPayslip, self).action_payslip_done()

        if not res:
            return res

        for payslip in self:
            if payslip.move_id:
                for slip_line in payslip.line_ids:
                    for move_line in payslip.move_id.line_ids:
                        if slip_line.name == move_line.name:
                            move_line.write({'analytic_tag_ids': [(6, 0, slip_line.analytic_tag_ids.ids)]})

        return res


class HrPayslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    analytic_tag_ids = fields.Many2many('account.analytic.tag', 'hr_payslip_analytic_tags_rel', 'line_id', 'analytic_tag_id', string='Analytic Tags')


class Contract(models.Model):
    _inherit = "hr.contract"

    analytic_tag_ids = fields.Many2many('account.analytic.tag', 'hr_contracts_analytic_tags_rel', 'contract_id', 'analytic_tag_id', string='Analytic Tags')


class HrSalaryRule(models.Model):
    _inherit = "hr.salary.rule"

    analytic_tag_ids = fields.Many2many('account.analytic.tag', 'hr_salary_rule_analytic_tags_rel', 'salary_rule_id', 'analytic_tag_id', string='Analytic Tags')
