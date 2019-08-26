# -*- coding: utf-8 -*-

from odoo import fields, models, api, _


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    email_sent = fields.Boolean(copy=False, readonly=True)

    # auxiliary fields
    email_status = fields.Selection(
        [('not_sent', 'Not Sent'), ('sent', 'Sent')], string='Email Status',
        compute='_compute_email_status')

    @api.multi
    def _compute_email_status(self):
        for invoice in self:
            invoice.email_status = 'sent' if invoice.email_sent else 'not_sent'

    def action_custom_invoice_sent(self):
        template_obj = self.env['mail.template']

        active_ids = self._context.get('active_ids')
        invoices = self.env['account.invoice'].browse(active_ids).filtered(
            lambda x: x.state in ['open', 'paid'])

        template = self.env.ref('account.email_template_edi_invoice')

        for invoice in invoices:
            template_obj.browse(template.id).send_mail(invoice.id)

            invoice = invoice.with_context(mail_post_autofollow=True)
            invoice.message_post(body=_("Invoice sent"))

        invoices.write({'sent': True, 'email_sent': True})
        return {}


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.multi
    def send_mail(self, auto_commit=False):
        res = super(MailComposeMessage, self).send_mail(
            auto_commit=auto_commit)

        context = self._context
        if context.get('default_model') == 'account.invoice' and context.get(
                'default_res_id') and context.get('mark_invoice_as_sent'):
            invoice = self.env['account.invoice'].browse(
                context['default_res_id'])
            invoice.email_sent = True
        return res
