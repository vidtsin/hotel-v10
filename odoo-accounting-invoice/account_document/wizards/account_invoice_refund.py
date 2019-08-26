# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.addons.account.models.account_invoice import TYPE2REFUND


class AccountInvoiceRefund(models.TransientModel):
    """Refunds invoice"""

    _inherit = "account.invoice.refund"

    @api.model
    def _get_invoice_id(self):
        invoice = self.env['account.invoice'].browse(
            self._context.get('active_ids', False))
        # we dont force one for compatibility with already running dsbs
        if len(invoice) > 1:
            raise UserError(_(
                'Refund wizard must be call only from one invoice'))
        return invoice

    invoice_id = fields.Many2one(
        'account.invoice',
        'Invoice',
        default=_get_invoice_id,
    )
    use_documents = fields.Boolean(
        related='invoice_id.journal_id.use_documents',
        string='Use Documents?',
        readonly=True,
    )
    journal_document_type_id = fields.Many2one(
        'account.journal.document.type',
        'Document Type',
        ondelete='cascade',
    )
    document_sequence_id = fields.Many2one(
        related='journal_document_type_id.sequence_id',
        readonly=True,
    )
    document_number = fields.Char(
        string='Document Number',
    )
    available_journal_document_type_ids = fields.Many2many(
        'account.journal.document.type',
        compute='get_available_journal_document_types',
        string='Available Journal Document Types',
    )
    type = fields.Selection([('debit','Debit Note'),('credit','Credit Note')],
                            translate=True,
                            string="Select Type",
                            default="credit",
                            required=True)

    @api.multi
    @api.depends('invoice_id','type')
    def get_available_journal_document_types(self):
        for rec in self:
            invoice = rec.invoice_id
            if not invoice:
                return True
            invoice_type = TYPE2REFUND[invoice.type]
            if rec.type == 'debit':
                invoice_type = TYPE2REFUND[invoice_type]
            res = invoice._get_available_journal_document_types(invoice.journal_id, invoice_type, invoice.partner_id)
            rec.available_journal_document_type_ids = res['available_journal_document_types']
            rec.journal_document_type_id = res['journal_document_type']

    @api.onchange('invoice_id','type')
    def _onchange_invoice_id_2(self):
        if self.invoice_id.id:
            invoice_type = TYPE2REFUND[self.invoice_id.type]
            if self.type == 'debit':
                invoice_type = TYPE2REFUND[invoice_type]
            res = self.invoice_id._get_available_journal_document_types(self.invoice_id.journal_id, invoice_type, self.invoice_id.partner_id)

            return {'domain': {'journal_document_type_id': [('id','in',res['available_journal_document_types'].ids)]}}

    @api.multi
    def compute_refund(self, mode='refund'):
        res = super(AccountInvoiceRefund, self.with_context(
            default_journal_document_type_id=self.journal_document_type_id.id,
            default_document_number=self.document_number)).compute_refund(mode=mode)
        if self.type == 'debit':
            nc_id = res['domain'][1][2]
            nc = self.env['account.invoice'].search([('id', '=', int(nc_id[0]))])
            if nc.type == 'out_refund':
                nc.write({'type': 'out_invoice'})
            if nc.type == 'in_refund':
                nc.write({'type': 'in_invoice'})
        return res

    @api.onchange('document_number')
    def onchange_document_number(self):
        if not self.document_number:
            return

        number = ''
        sep = ' '
        document_number = self.document_number
        if '-' in document_number:
            sep = '-'
        elements = document_number.split(sep)
        if len(elements) == 2:
            if (len(elements[0]) <= 5) and (len(elements[0]) <= 8):
                number = '%s-%s' % (elements[0].zfill(4), elements[1].zfill(8))
        else:
            number = document_number

        self.document_number = number
