from odoo import models, fields, api, _
from datetime import datetime
from dateutil import relativedelta


class SaleSubscription(models.Model):
    _inherit = "sale.subscription"

    @api.returns('account.invoice')
    def _recurring_create_invoice2(self, automatic=False):
        invoices = self._recurring_create_invoice(automatic)
        invs = self.env['account.invoice'].browse(invoices)
        for inv in invs:
            if inv.afip_concept in ['2', '3']:
                inv.afip_service_start = self.recurring_next_date
                end_date = datetime.strptime(self.recurring_next_date, "%Y-%m-%d").date()
                months = days = years = 0
                if self.template_id.recurring_rule_type == 'daily':
                    days = self.template_id.recurring_interval
                if self.template_id.recurring_rule_type == 'weekly':
                    days = self.template_id.recurring_interval * 7
                if self.template_id.recurring_rule_type == 'monthly':
                    months = self.template_id.recurring_interval
                    days -= 1
                if self.template_id.recurring_rule_type == 'yearly':
                    years = self.template_id.recurring_interval
                    days -= 1
                inv.afip_service_end = end_date + relativedelta.relativedelta(months=months, days=days, years=years)
        return invoices

    @api.multi
    def recurring_invoice(self):
        self._recurring_create_invoice2()
        return self.action_subscription_invoice()
